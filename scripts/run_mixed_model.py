"""Mixed-Model Negotiation Runner.
Assigns distinct, asymmetric LLM providers/models to each company in the joint venture:
  - G-Corp: Chip designer (e.g. Claude)
  - Yang Industries: Manufacturer (e.g. GPT-6 Luna / Ollama)
  - Chang-Liu Cloud Services: Cloud provider (e.g. Gemini)

Supports single or multi-condition execution and optional Latin Square model rotation.

Examples:
  python scripts/run_mixed_model.py --condition board_vote --runs 1
  python scripts/run_mixed_model.py --conditions mbrp free board_vote arbitrator --runs 1
  python scripts/run_mixed_model.py --rotate --runs 3
"""

import os
import sys
import argparse
import time
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.orchestrator import run_single_negotiation

COMPANIES = ["G-Corp", "Yang Industries", "Chang-Liu Cloud Services"]
DEFAULT_CONDITIONS = ["mbrp", "free", "board_vote", "arbitrator"]

FIXED_ARBITRATOR_CONFIG = {
    "provider": "gemini",
    "model_name": "gemini-3.8-flash",
    "thinking_level": "LOW",
}

BASE_MODELS = [
    {"provider": "anthropic", "model_name": "claude-haiku-5-5"},
    {"provider": "openai", "model_name": "gpt-6-luna"},
    {"provider": "gemini", "model_name": "gemini-3.8-flash", "thinking_level": "LOW"},
]

OLLAMA_MODELS = [
    {"provider": "anthropic", "model_name": "claude-haiku-5-5"},
    {"provider": "openai", "model_name": "gpt-oss:20b", "base_url": "http://localhost:11434/v1", "api_key": "ollama"},
    {"provider": "gemini", "model_name": "gemini-3.8-flash", "thinking_level": "LOW"},
]


def get_agent_allocation(run_index: int, rotate: bool = False, use_ollama: bool = False) -> Dict[str, Dict[str, Any]]:
    """Assigns models to companies, optionally rotating models via Latin Square round-robin."""
    models_pool = OLLAMA_MODELS if use_ollama else BASE_MODELS
    shift = (run_index % 3) if rotate else 0

    allocation: Dict[str, Dict[str, Any]] = {}
    for idx, comp in enumerate(COMPANIES):
        model_idx = (idx + shift) % 3
        allocation[comp] = dict(models_pool[model_idx])
    return allocation


def main():
    parser = argparse.ArgumentParser(description="Run mixed-model bargaining experiments")
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=None,
        help="Conditions to run: mbrp, free, board_vote, arbitrator (default: all 4)",
    )
    parser.add_argument(
        "--condition",
        choices=["free", "board_vote", "mbrp", "arbitrator"],
        default=None,
        help="Single condition shorthand (e.g. --condition board_vote)",
    )
    parser.add_argument("--runs", type=int, default=1, help="Number of repetitions per condition (default: 1)")
    parser.add_argument("--use-ollama", action="store_true", help="Use local Ollama gpt-oss for Yang Industries")
    parser.add_argument(
        "--rotate",
        action="store_true",
        help="Rotate models across companies on each run using Latin Square round-robin (eliminates role confound)",
    )
    args = parser.parse_args()

    if args.condition:
        conditions = [args.condition]
    elif args.conditions:
        conditions = args.conditions
    else:
        conditions = DEFAULT_CONDITIONS

    print("=" * 70)
    print("MIXED-MODEL MULTI-AGENT EXPERIMENT")
    print(f"Conditions: {', '.join(conditions)}")
    print(f"Runs/cell:  {args.runs}")
    print(f"Rotation:   {'Enabled (Latin Square Round-Robin)' if args.rotate else 'Disabled (Static Allocation)'}")
    print("=" * 70)

    for cond in conditions:
        print(f"\n==================== Condition: {cond.upper()} ====================")
        for i in range(args.runs):
            agent_cfg = get_agent_allocation(run_index=i, rotate=args.rotate, use_ollama=args.use_ollama)
            shift_tag = f" (Shift {i % 3})" if args.rotate else ""
            print(f"\n[Run {i + 1}/{args.runs}]{shift_tag} Active Model Allocation:")
            for comp, c in agent_cfg.items():
                print(f"  - {comp:25s}: {c['provider']} ({c['model_name']})")
            if cond == "arbitrator":
                print(f"  - {'Neutral Arbitrator':25s}: {FIXED_ARBITRATOR_CONFIG['provider']} ({FIXED_ARBITRATOR_CONFIG['model_name']}, Thinking: {FIXED_ARBITRATOR_CONFIG['thinking_level']})")

            run_id = f"mixed_{cond}_{int(time.time())}_{i + 1}"
            print(f"Executing {run_id}...")
            t0 = time.time()
            try:
                res = run_single_negotiation(
                    run_id=run_id,
                    condition_id=cond,
                    agent_configs=agent_cfg,
                    arbitrator_config=FIXED_ARBITRATOR_CONFIG,
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

    print("\n" + "=" * 70)
    print("MIXED-MODEL EXPERIMENT COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    main()
