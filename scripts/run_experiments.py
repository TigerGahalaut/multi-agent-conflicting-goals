"""Phase 7: Master Experiment Runner for Homogeneous Multi-Agent Negotiations.
Iterates over conditions x models x runs with checkpointing and resumability.
Supports all models configured in config.yaml:
  - Gemini: gemini_flash_lite, gemini_flash
  - Anthropic: claude (claude-haiku-5-5)
  - OpenAI: gpt (gpt-4o), gpt_oss (gpt-oss:20b via Ollama)

Examples:
  python scripts/run_experiments.py --models claude --conditions board_vote --runs 1
  python scripts/run_experiments.py --models gpt --conditions free --runs 2
  python scripts/run_experiments.py --models gemini_flash gemini_flash_lite --conditions mbrp board_vote arbitrator --runs 10
"""

import sys
import os
import time
import argparse
import yaml
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.orchestrator import run_single_negotiation
from src.storage import SUMMARY_CSV_PATH

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
DEFAULT_CONDITIONS = ["mbrp", "board_vote", "arbitrator"]
DEFAULT_RUNS = 10


def load_configured_models() -> Dict[str, Dict[str, Any]]:
    """Loads all models defined in config.yaml, normalizing model keys and parameters."""
    if not CONFIG_PATH.exists():
        return {
            "gemini_flash_lite": {"provider": "gemini", "model_name": "gemini-3.5-flash-lite", "thinking_level": "MINIMAL"},
            "gemini_flash": {"provider": "gemini", "model_name": "gemini-3.8-flash", "thinking_level": "LOW"},
        }
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    raw_models = cfg.get("models", {})
    models: Dict[str, Dict[str, Any]] = {}
    for key, m_cfg in raw_models.items():
        if key in ("tier_a", "tier_b"):
            continue
        model_name = m_cfg.get("name") or m_cfg.get("model")
        if not model_name:
            continue
        models[key] = {
            "key": key,
            "provider": m_cfg.get("provider", "gemini"),
            "model_name": model_name,
            "thinking_level": m_cfg.get("thinking_level", "MINIMAL"),
            "temperature": m_cfg.get("temperature"),
            "base_url": m_cfg.get("base_url"),
            "api_key": m_cfg.get("api_key"),
        }
    return models


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
    configured_models = load_configured_models()

    parser = argparse.ArgumentParser(description="Master Experiment Runner for Homogeneous Multi-Agent Negotiations")
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=None,
        help="Conditions to run: mbrp, free, board_vote, arbitrator (default: mbrp, board_vote, arbitrator)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help=f"Models to run: {', '.join(configured_models.keys())} (default: gemini_flash_lite, gemini_flash)",
    )
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help="Number of repetitions per cell (default 10)")
    parser.add_argument("--overwrite", action="store_true", help="Re-run games even if already present in summary.csv")
    args = parser.parse_args()

    conditions = args.conditions if args.conditions else DEFAULT_CONDITIONS
    runs_per_cell = args.runs

    selected_models: List[Dict[str, Any]] = []
    if args.models:
        for m_arg in args.models:
            matched = False
            for k, m_data in configured_models.items():
                if m_arg in (k, m_data["model_name"]):
                    selected_models.append(m_data)
                    matched = True
                    break
            if not matched:
                print(f"[WARNING] Model '{m_arg}' not found in config.yaml. Known models: {list(configured_models.keys())}")
    else:
        default_keys = ["gemini_flash_lite", "gemini_flash"]
        selected_models = [configured_models[k] for k in default_keys if k in configured_models]
        if not selected_models:
            selected_models = list(configured_models.values())

    if not selected_models:
        print("[ERROR] No valid models selected. Exiting.")
        sys.exit(1)

    print("=" * 70)
    print("MASTER EXPERIMENT RUNNER (HOMOGENEOUS AGENTS)")
    print(f"Conditions: {', '.join(conditions)}")
    print(f"Models:     {', '.join(m['key'] + ' (' + m['provider'] + ':' + m['model_name'] + ')' for m in selected_models)}")
    print(f"Runs/cell:  {runs_per_cell}")
    print("=" * 70)

    completed = get_completed_run_ids()
    print(f"Detected {len(completed)} previously completed runs in summary.csv.\n")

    total_planned = len(conditions) * len(selected_models) * runs_per_cell
    run_counter = 0

    for model_cfg in selected_models:
        m_key = model_cfg["key"]
        provider = model_cfg["provider"]
        model_name = model_cfg["model_name"]
        thinking_level = model_cfg["thinking_level"]
        temperature = model_cfg.get("temperature")
        base_url = model_cfg.get("base_url")
        api_key = model_cfg.get("api_key")

        for cond in conditions:
            print(f"\n--- Condition: {cond.upper()} | Model: {m_key} ({provider}:{model_name}) ---")

            for r_idx in range(runs_per_cell):
                run_counter += 1
                run_id = f"{cond}_{model_name}_{r_idx + 1}"

                if run_id in completed and not args.overwrite:
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
                        provider=provider,
                        temperature=temperature,
                        base_url=base_url,
                        api_key=api_key,
                        run_index=r_idx,
                        max_rounds=8,
                    )
                    elapsed = time.time() - t0
                    status = "DEAL" if res.deal_reached else "DEADLOCK"
                    tokens = res.token_usage.get("total_tokens", 0)
                    print(f"    -> Done in {elapsed:.1f}s | {status} (Round {res.rounds_taken}) | Tokens: {tokens} | Split: {res.agreed_allocation}")
                    completed.add(run_id)

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
