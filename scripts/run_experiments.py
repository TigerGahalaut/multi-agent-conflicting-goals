"""Phase 7: Master Experiment Runner for the full 60-run matrix.
Iterates over 3 conditions x 2 model tiers x 10 runs with checkpointing and resumability.
"""

import sys
import os
import time
import argparse
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.orchestrator import run_single_negotiation
from src.storage import SUMMARY_CSV_PATH

DEFAULT_CONDITIONS = ["mbrp", "board_vote", "arbitrator"]
AVAILABLE_MODELS = [
    {"name": "gemini-3.5-flash-lite", "thinking_level": "MINIMAL"},
    {"name": "gemini-3.8-flash", "thinking_level": "LOW"},
]
DEFAULT_RUNS = 10


def get_completed_run_ids() -> set:
    """Returns the set of run_ids already saved in summary.csv."""
    if not SUMMARY_CSV_PATH.exists():
        return set()
    try:
        df = pd.read_csv(SUMMARY_CSV_PATH)
        return set(df["run_id"].dropna().unique())
    except Exception:
        return set()


def main():
    parser = argparse.ArgumentParser(description="Master Experiment Runner")
    parser.add_argument("--conditions", nargs="+", default=None, help="Conditions to run: mbrp, free, board_vote, arbitrator")
    parser.add_argument("--models", nargs="+", default=None, help="Models to run: gemini-3.5-flash-lite, gemini-3.8-flash")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help="Number of repetitions per cell (default 10)")
    args = parser.parse_args()

    conditions = args.conditions if args.conditions else DEFAULT_CONDITIONS
    runs_per_cell = args.runs

    if args.models:
        models = [m for m in AVAILABLE_MODELS if m["name"] in args.models]
    else:
        models = AVAILABLE_MODELS

    print("=" * 70)
    print("MASTER EXPERIMENT RUNNER")
    print(f"Conditions: {', '.join(conditions)} | Runs per cell: {runs_per_cell}")
    print("=" * 70)

    completed = get_completed_run_ids()
    print(f"Detected {len(completed)} previously completed runs. Resuming remaining runs...\n")

    total_planned = len(conditions) * len(models) * runs_per_cell
    run_counter = 0

    for model_cfg in models:
        model_name = model_cfg["name"]
        thinking_level = model_cfg["thinking_level"]

        for cond in conditions:
            print(f"\n--- Condition: {cond.upper()} | Model: {model_name} (Thinking: {thinking_level}) ---")

            for r_idx in range(runs_per_cell):
                run_counter += 1
                run_id = f"{cond}_{model_name}_{r_idx + 1}"

                if run_id in completed:
                    print(f"[{run_counter}/{total_planned}] Skipping already completed run: {run_id}")
                    continue

                print(f"[{run_counter}/{total_planned}] Starting {run_id}...")
                t0 = time.time()
                try:
                    res = run_single_negotiation(
                        run_id=run_id,
                        condition_id=cond,
                        model_name=model_name,
                        thinking_level=thinking_level,
                        run_index=r_idx,
                        max_rounds=8,
                    )
                    elapsed = time.time() - t0
                    status = "DEAL" if res.deal_reached else "DEADLOCK"
                    tokens = res.token_usage.get("total_tokens", 0)
                    print(f"    -> Done in {elapsed:.1f}s | {status} (Round {res.rounds_taken}) | Tokens: {tokens} | Split: {res.agreed_allocation}")
                    completed.add(run_id)

                    # Polite 1-second pause between runs to avoid rate limits
                    time.sleep(1.0)

                except Exception as e:
                    print(f"    -> ERROR in run {run_id}: {e}")
                    print("Pausing 5s before continuing...")
                    time.sleep(5.0)

    print("\n" + "=" * 70)
    print("EXPERIMENT RUN COMPLETE!")
    print(f"All available runs recorded in {SUMMARY_CSV_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    main()
