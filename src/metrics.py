"""Analysis and metric calculation module for experiment results."""

from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


def load_results_df(csv_path: str = "results/summary.csv") -> pd.DataFrame:
    """Loads and formats the summary CSV."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Results summary not found at {csv_path}")
    return pd.read_csv(path)


def compute_governance_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """Computes deal rate, average rounds, and mean surplus by condition and model."""
    grouped = df.groupby(["condition_id", "model_name"]).agg(
        total_runs=("run_id", "count"),
        deal_rate=("deal_reached", "mean"),
        avg_rounds=("rounds_taken", "mean"),
        avg_surplus=("surplus_realized", "mean"),
        avg_nash_distance=("nash_distance", lambda s: s.dropna().mean() if not s.dropna().empty else np.nan),
    ).reset_index()
    grouped["deal_rate"] = (grouped["deal_rate"] * 100).round(1)
    grouped["avg_rounds"] = grouped["avg_rounds"].round(2)
    grouped["avg_surplus"] = grouped["avg_surplus"].round(0)
    grouped["avg_nash_distance"] = grouped["avg_nash_distance"].round(1)
    return grouped


def compute_payoffs_table(df: pd.DataFrame) -> pd.DataFrame:
    """Computes mean realized payoffs by company across conditions."""
    grouped = df.groupby(["condition_id", "model_name"]).agg(
        mean_g_corp=("payoff_g_corp", "mean"),
        mean_yang=("payoff_yang", "mean"),
        mean_chang_liu=("payoff_chang_liu", "mean"),
        violation_rate_g_corp=("violation_g_corp", "mean"),
        violation_rate_yang=("violation_yang", "mean"),
        violation_rate_chang_liu=("violation_chang_liu", "mean"),
    ).reset_index()

    for col in ["mean_g_corp", "mean_yang", "mean_chang_liu"]:
        grouped[col] = grouped[col].round(0)
    for col in ["violation_rate_g_corp", "violation_rate_yang", "violation_rate_chang_liu"]:
        grouped[col] = (grouped[col] * 100).round(1)
    return grouped


def compute_coalition_frequencies(df: pd.DataFrame) -> pd.DataFrame:
    """Computes coalition frequencies under Board Vote."""
    bv = df[df["condition_id"] == "board_vote"].copy()
    if bv.empty:
        return pd.DataFrame()

    bv["coalition_pair"] = bv["winning_voters"].apply(
        lambda s: " + ".join(sorted(s.split(";"))) if pd.notna(s) and s else "No Deal"
    )

    summary = bv.groupby(["model_name", "coalition_pair", "approval_type"]).size().reset_index(name="count")
    return summary
