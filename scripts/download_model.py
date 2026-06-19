from __future__ import annotations

import argparse
import os
import sys
import urllib.request

MODELS = {
    "qwen3-8b": {
        "url": "https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/main/Qwen3-8B-Q4_K_M.gguf",
        "size_gb": 5.2,
    },
    "llama3-8b": {
        "url": "https://huggingface.co/bartowski/Llama-3.1-8B-Instruct-GGUF/resolve/main/Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "size_gb": 4.9,
    },
    "gemma3-12b": {
        "url": "https://huggingface.co/google/gemma-3-12b-it-GGUF/resolve/main/gemma-3-12b-it-Q4_K_M.gguf",
        "size_gb": 7.5,
    },
    "phi3-mini": {
        "url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf",
        "size_gb": 2.3,
    },
}


def parse_args():
    parser = argparse.ArgumentParser(description="Download a GGUF model for MOSO")
    parser.add_argument("model", nargs="?", choices=list(MODELS.keys()) + ["list"],
                        default="list", help="Model key to download")
    parser.add_argument("--dir", default="models",
                        help="Directory to save the model (default: models/)")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.model == "list":
        print("Available models:")
        print()
        for key, info in MODELS.items():
            print(f"  {key:15s} ~{info['size_gb']}GB  {info['url']}")
        print()
        print("Usage: python scripts/download_model.py <model_name>")
        return
    info = MODELS.get(args.model)
    if not info:
        print(f"Unknown model: {args.model}")
        sys.exit(1)
    os.makedirs(args.dir, exist_ok=True)
    dest = os.path.join(args.dir, info["url"].split("/")[-1])
    print(f"Downloading {args.model} (~{info['size_gb']}GB)...")
    print(f"  From: {info['url']}")
    print(f"  To:   {dest}")
    print()
    print("This will take a while depending on your internet speed.")
    if not os.environ.get("OPCODE_NONINTERACTIVE"):
        confirm = input("Continue? [y/N] ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            return

    def report(block, blocks, size):
        downloaded = block * size / (1024 * 1024)
        total = blocks * size / (1024 * 1024) if blocks > 0 else 1
        pct = min(100, block * size * 100 / max(1, blocks * size)) if blocks > 0 else 0
        bar = "#" * int(pct / 5) + "-" * (20 - int(pct / 5))
        print(f"\r  [{bar}] {downloaded:.0f}/{total:.0f}MB ({pct:.0f}%)", end="")
        if block * size >= blocks * size and blocks > 0:
            print()

    try:
        urllib.request.urlretrieve(info["url"], dest, reporthook=report)
        print(f"\nDownloaded to: {dest}")
        print(f"\nTo use with MOSO:")
        print(f'  python -c "from moso_core.llm.backend import LlamaServer; from moso_core.llm.models import LLMConfig; s = LlamaServer(LLMConfig(model_path=r\'{dest}\')); s.start(); print(s.complete()); s.stop()"')
    except KeyboardInterrupt:
        print("\nCancelled.")
        if os.path.isfile(dest):
            os.remove(dest)


if __name__ == "__main__":
    main()
