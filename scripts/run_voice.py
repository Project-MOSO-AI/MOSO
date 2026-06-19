"""
MOSO Voice Mode - Interactive voice CLI demo.

Usage:
    python -m scripts.run_voice --model <path/to/model> [--backend llama|onnx]

Requires:
    - A working microphone
    - Voice models (whisper, piper, ecapa) -- run download_voice_models.py first
"""

import argparse
import logging
import sys
import time

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_voice")


def parse_args():
    parser = argparse.ArgumentParser(description="MOSO Voice Mode CLI")
    parser.add_argument("--model", required=True, help="Path to LLM model file")
    parser.add_argument("--backend", default="llama", choices=["llama", "onnx"],
                        help="Inference backend (default: llama)")
    parser.add_argument("--whisper-size", default="base",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size (default: base)")
    parser.add_argument("--no-safety", action="store_true", help="Disable safety guards")
    parser.add_argument("--ctx", type=int, default=2048, help="Context window size")
    parser.add_argument("--gpu-layers", type=int, default=0, help="GPU layers for llama.cpp")
    parser.add_argument("--max-tokens", type=int, default=256, help="Max tokens per response")
    parser.add_argument("--no-speaker-verify", action="store_true",
                        help="Disable speaker verification")
    parser.add_argument("--enroll", action="store_true",
                        help="Enroll speaker before starting voice mode")
    return parser.parse_args()


def enroll_speaker(verifier, num_samples: int = 3):
    from moso_core.voice.input import AudioStream, AudioConfig

    print("\n=== Speaker Enrollment ===")
    print(f"I'll record {num_samples} short audio samples.")
    print("Please speak naturally in a quiet environment.\n")

    config = AudioConfig(silence_duration_ms=1000)
    stream = AudioStream(config)
    stream.start()

    try:
        for i in range(num_samples):
            input(f"Press Enter and speak sample {i + 1}/{num_samples}...")
            print("Recording...")

            audio_chunks = []
            start = time.time()
            while time.time() - start < 3.0:
                chunk = stream.read_audio(timeout=0.5)
                if chunk is not None:
                    audio_chunks.append(chunk)

            if audio_chunks:
                combined = np.concatenate(audio_chunks, axis=0)
                verifier.enroll([combined], name="owner")
                print(f"  Sample {i + 1} recorded ({len(audio_chunks)} chunks, {len(combined)} samples).\n")
            else:
                print("  No audio detected. Try again.")
                i -= 1

    finally:
        stream.stop()

    print("Speaker enrollment complete!\n")


def main():
    args = parse_args()

    if args.enroll:
        from moso_core.voice.speaker import SpeakerVerifier
        verifier = SpeakerVerifier()
        verifier._embedder.load_model()
        enroll_speaker(verifier)
        if not args.model:
            return

    from moso_core.inference.base import InferenceConfig
    from moso_core.orchestration.orchestrator import Orchestrator
    from moso_core.voice.stt import WhisperSTT
    from moso_core.voice.tts import PiperTTS
    from moso_core.voice.speaker import SpeakerVerifier
    from moso_core.voice.input import AudioStream, AudioConfig

    config = InferenceConfig(
        model_path=args.model,
        n_ctx=args.ctx,
        n_gpu_layers=args.gpu_layers,
        max_tokens=args.max_tokens,
    )

    logger.info("Initializing MOSO Voice Mode with model: %s", args.model)
    start = time.perf_counter()

    with Orchestrator(config=config, enable_safety=not args.no_safety, backend=args.backend) as orchestrator:
        logger.info("Loading voice models...")
        orchestrator.enable_voice(
            stt_model=WhisperSTT(model_size=args.whisper_size),
            tts_model=PiperTTS(),
            speaker_verifier=None if args.no_speaker_verify else SpeakerVerifier(),
        )

        elapsed = time.perf_counter() - start
        logger.info("MOSO Voice ready in %.2fs", elapsed)

        audio_config = AudioConfig()
        audio_stream = AudioStream(audio_config)
        audio_stream.start()

        print("\n" + "=" * 60)
        print("  MOSO Voice Mode")
        print("  Say 'Hey MOSO' followed by your command")
        print("  Press Ctrl+C to exit")
        print("=" * 60 + "\n")

        try:
            while True:
                audio = audio_stream.read_audio(timeout=1.0)
                if audio is None:
                    continue

                result = orchestrator.process_voice(audio)
                if result.error:
                    continue
                if result.text:
                    print(f"\nYou (voice): {result.stt_result.text}")
                    print(f"M0S0 (voice): {result.text}\n")
                    if result.verification:
                        status = (
                            "verified" if result.verification.verified
                            else "guest"
                        )
                        print(f"  [{status}] confidence: {result.verification.confidence:.2f}")

        except KeyboardInterrupt:
            print("\nGoodbye!")
        finally:
            audio_stream.stop()


if __name__ == "__main__":
    main()
