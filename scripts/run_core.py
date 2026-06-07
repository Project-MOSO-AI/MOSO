"""
MOSO Core - Interactive CLI Demo

Usage:
    python -m scripts.run_core --model <path/to/model.gguf>

Example:
    python -m scripts.run_core --model models/llm/phi3/Phi-3-mini-4k-instruct-q4.gguf
"""

import argparse
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_core")


def parse_args():
    parser = argparse.ArgumentParser(description="MOSO Core CLI Demo")
    parser.add_argument("--model", required=True, help="Path to GGUF model file")
    parser.add_argument("--no-safety", action="store_true", help="Disable safety guards")
    parser.add_argument("--ctx", type=int, default=2048, help="Context window size")
    parser.add_argument("--gpu-layers", type=int, default=0, help="GPU layers to offload")
    parser.add_argument("--max-tokens", type=int, default=512, help="Max tokens per response")
    parser.add_argument("--agent", action="store_true", help="Use agent mode")
    return parser.parse_args()


def run_chat(orchestrator):
    print("\n" + "=" * 60)
    print("  MOSO AI - Interactive Chat (type 'exit' to quit, 'reset' to restart)")
    print("=" * 60 + "\n")

    while True:
        try:
            user_input = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("Goodbye!")
            break
        if user_input.lower() == "reset":
            orchestrator.reset_conversation()
            print("Conversation reset.\n")
            continue

        print("M0S0 > ", end="", flush=True)
        start = time.perf_counter()
        collected = []
        for chunk in orchestrator.process_stream(user_input):
            print(chunk, end="", flush=True)
            collected.append(chunk)
        elapsed = time.perf_counter() - start

        full = "".join(collected)
        token_count = max(1, len(full.split()))
        print(f"\n\n      └─ {token_count} words in {elapsed:.1f}s "
              f"({token_count / elapsed:.1f} words/s)\n")


def run_agent(orchestrator):
    from moso_core.agents.base import SimpleAgent, ToolSpec

    agent = SimpleAgent("M0S0-Agent", backend=orchestrator.backend)
    agent.register_tool(
        ToolSpec(
            name="calculator",
            description="Perform arithmetic calculations",
            parameters={
                "expression": {
                    "type": "string",
                    "description": "Math expression to evaluate, e.g. '2 + 2'",
                }
            },
        )
    )

    print("\n" + "=" * 60)
    print("  MOSO AI - Agent Mode (type 'exit' to quit)")
    print("=" * 60 + "\n")

    while True:
        try:
            task = input("Task > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not task:
            continue
        if task.lower() in ("exit", "quit", "q"):
            print("Goodbye!")
            break

        print("\nM0S0-Agent thinking...\n")
        result = agent.run(task)
        print(f"Result: {result.output}\n")


def main():
    args = parse_args()

    from moso_core.inference.base import InferenceConfig
    from moso_core.orchestration.orchestrator import Orchestrator

    config = InferenceConfig(
        model_path=args.model,
        n_ctx=args.ctx,
        n_gpu_layers=args.gpu_layers,
        max_tokens=args.max_tokens,
    )

    logger.info("Initializing MOSO Core with model: %s", args.model)
    start = time.perf_counter()

    with Orchestrator(config=config, enable_safety=not args.no_safety) as orchestrator:
        elapsed = time.perf_counter() - start
        logger.info("MOSO Core ready in %.2fs", elapsed)

        if args.agent:
            run_agent(orchestrator)
        else:
            run_chat(orchestrator)


if __name__ == "__main__":
    main()
