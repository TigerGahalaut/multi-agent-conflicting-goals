"""Persistence layer: writing JSONL event transcripts and tabular CSV summaries."""

import json
import csv
import os
from pathlib import Path
from typing import List
from src.schemas import RoundEvent, RunResult

TRANSCRIPTS_DIR = Path("transcripts")
RESULTS_DIR = Path("results")
SUMMARY_CSV_PATH = RESULTS_DIR / "summary.csv"


def ensure_directories():
    """Ensures transcript and results directories exist."""
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def save_transcript(events: List[RoundEvent], run_id: str, condition_id: str, model_name: str) -> str:
    """
    Saves the full event stream of a run to a JSONL file.
    Returns the file path.
    """
    ensure_directories()
    safe_model = model_name.replace("/", "_")
    filename = f"{condition_id}_{safe_model}_{run_id}.jsonl"
    filepath = TRANSCRIPTS_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        for event in events:
            f.write(event.model_dump_json() + "\n")

    return str(filepath)


def append_summary_csv(result: RunResult) -> str:
    """
    Appends a run's top-level metrics to the summary CSV file.
    Creates header if file does not exist.
    """
    ensure_directories()
    file_exists = SUMMARY_CSV_PATH.exists()

    row = {
        "run_id": result.run_id,
        "condition_id": result.condition_id,
        "model_name": result.model_name,
        "thinking_level": result.thinking_level,
        "model_version": result.model_version or "",
        "deal_reached": result.deal_reached,
        "rounds_taken": result.rounds_taken,
        "surplus_realized": result.surplus_realized,
        "approval_type": result.approval_type or "",
        "winning_voters": ";".join(result.winning_voters) if result.winning_voters else "",
        "payoff_g_corp": result.realized_payoff.get("G-Corp", 0),
        "payoff_yang": result.realized_payoff.get("Yang Industries", 0),
        "payoff_chang_liu": result.realized_payoff.get("Chang-Liu Cloud Services", 0),
        "violation_g_corp": result.outside_option_violations.get("G-Corp", False),
        "violation_yang": result.outside_option_violations.get("Yang Industries", False),
        "violation_chang_liu": result.outside_option_violations.get("Chang-Liu Cloud Services", False),
        "nash_distance": round(result.nash_distance, 2) if result.nash_distance is not None else "",
        "two_vs_one_nash": result.two_vs_one_nash if result.two_vs_one_nash is not None else False,
        "squeezed_firm": result.squeezed_firm or "",
        "outvoted_firm_bound": result.outvoted_firm_bound if result.outvoted_firm_bound is not None else False,
        "below_walkaway_imposed": result.below_walkaway_imposed if result.below_walkaway_imposed is not None else False,
        "imposed_on": result.imposed_on or "",
        "below_walkaway_accepted": result.below_walkaway_accepted if result.below_walkaway_accepted is not None else False,
        "first_claim_g_corp": result.first_disclosed_claims.get("G-Corp") or "",
        "first_claim_yang": result.first_disclosed_claims.get("Yang Industries") or "",
        "first_claim_chang_liu": result.first_disclosed_claims.get("Chang-Liu Cloud Services") or "",
        "final_claim_g_corp": result.final_disclosed_claims.get("G-Corp") or "",
        "final_claim_yang": result.final_disclosed_claims.get("Yang Industries") or "",
        "final_claim_chang_liu": result.final_disclosed_claims.get("Chang-Liu Cloud Services") or "",
        "claim_drift_g_corp": result.claim_drift.get("G-Corp") or "",
        "claim_drift_yang": result.claim_drift.get("Yang Industries") or "",
        "claim_drift_chang_liu": result.claim_drift.get("Chang-Liu Cloud Services") or "",
        "inflation_ratio_g_corp": result.inflation_ratio.get("G-Corp") if (result.inflation_ratio and result.inflation_ratio.get("G-Corp")) else "",
        "inflation_ratio_yang": result.inflation_ratio.get("Yang Industries") if (result.inflation_ratio and result.inflation_ratio.get("Yang Industries")) else "",
        "inflation_ratio_chang_liu": result.inflation_ratio.get("Chang-Liu Cloud Services") if (result.inflation_ratio and result.inflation_ratio.get("Chang-Liu Cloud Services")) else "",
        "prompt_tokens": result.token_usage.get("prompt_tokens", 0),
        "candidate_tokens": result.token_usage.get("candidate_tokens", 0),
        "total_tokens": result.token_usage.get("total_tokens", 0),
    }

    with open(SUMMARY_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    return str(SUMMARY_CSV_PATH)
