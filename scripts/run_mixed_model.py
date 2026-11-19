"""Mixed-Model Negotiation Runner.
Assigns distinct, asymmetric LLM providers/models to each company in the joint venture:
  - G-Corp: Chip designer (e.g. Claude)
  - Yang Industries: Manufacturer (e.g. GPT-4o / Ollama)
  - Chang-Liu Cloud Services: Cloud provider (e.g. Gemini)
"""

import os
import sys
import argparse
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.orchestrator import run_single_negotiation


DEFAULT_MIXED_CONFIG = {
    "G-Corp": {
        "provider": "anthropic",
        "model_name": "claude-haiku-5-5",
    },
    "Yang Industries": {
        "provider": "openai",
        "model_name": "gpt-4o",
    },
    "Chang-Liu Cloud Services": {
        "provider": "gemini",
        "model_name": "gemini-3.8-flash",
        "thinking_level": "LOW",
    },
}

# Alternative local config using Ollama for Yang if no OpenAI key:
OLLAMA_FALLBACK_CONFIG = {
    "G-Corp": {
        "provider": "anthropic",
        "model_name": "claude-haiku-5-5",
    },
    "Yang Industries": {
        "provider": "openai",
        "model_name": "gpt-oss:20b",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
    },
    "Chang-Liu Cloud Services": {
        "provider": "gemini",
        "model_name": "gemini-3.8-flash",
        "thinking_level": "LOW",
    },
}


def main():
    parser = argparse.ArgumentParser(description="Run mixed-model bargaining experiments")
    parser.add_argument("--condition", choices=["free", "board_vote", "mbrp", "arbitrator"], default="board_vote", help="Condition to run")
    parser.add_argument("--runs", type=int, default=1, help="Number of repetitions to run")
    parser.add_argument("--use-ollama", action="store_true", help="Use local Ollama gpt-oss for Yang Industries")
    args = parser.parse_args()

    agent_cfg = OLLAMA_FALLBACK_CONFIG if args.use_ollama else DEFAULT_MIXED_CONFIG

    print("=" * 70)
    print("MIXED-MODEL MULTI-AGENT EXPERIMENT")
    print(f"Condition: {args.condition.upper()} | Runs: {args.runs}")
    print("Model Allocation:")
    for comp, c in agent_cfg.items():
        print(f"  - {comp:25s}: {c['provider']} ({c['model_name']})")
    print("=" * 70)

    for i in range(args.runs):
        run_id = f"mixed_{args.condition}_{int(time.time())}_{i+1}"
        print(f"\n[Run {i+1}/{args.runs}] Executing {run_id}...")
        t0 = time.time()
        try:
            res = run_single_negotiation(
                run_id=run_id,
                condition_id=args.condition,
                agent_configs=agent_cfg,
                run_index=i,
                max_rounds=8,
            )
            elapsed = time.time() - t0
            status = "DEAL" if res.deal_reached else "DEADLOCK"
            print(f"  -> Finished in {elapsed:.1f}s | Result: {status} (Round {res.rounds_taken})")
            print(f"     Allocation: {res.agreed_allocation}")
        except Exception as e:
            print(f"  -> ERROR during mixed execution: {e}")
            print("     Check that API keys are set in .env (ANTHROPIC_API_KEY, OPENAI_API_KEY).")


if __name__ == "__main__":
    main()
