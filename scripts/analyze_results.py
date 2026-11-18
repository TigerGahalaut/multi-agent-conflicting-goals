"""Phase 8: Analysis and Visualization Script.
Processes results/summary.csv and produces tables and publication-ready charts.
"""

import sys
import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.metrics import (
    load_results_df,
    compute_governance_summary_table,
    compute_payoffs_table,
    compute_coalition_frequencies,
    compute_coalition_breakdown,
    compute_honesty_strategic_disclosure_table,
    compute_company_honesty_summary,
)

RESULTS_DIR = Path("results")


def generate_plots(df: pd.DataFrame):
    """Generates charts for presentation and report."""
    sns.set_theme(style="whitegrid", palette="muted")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Deal Rate by Condition and Model
    plt.figure(figsize=(8, 5))
    deal_df = df.groupby(["condition_id", "model_name"])["deal_reached"].mean().reset_index()
    deal_df["deal_rate_pct"] = deal_df["deal_reached"] * 100
    ax = sns.barplot(
        data=deal_df,
        x="condition_id",
        y="deal_rate_pct",
        hue="model_name",
        palette="viridis"
    )
    plt.title("Deal Completion Rate by Governance Mechanism and Model", fontsize=13, fontweight="bold")
    plt.xlabel("Governance Condition", fontsize=11)
    plt.ylabel("Deal Rate (%)", fontsize=11)
    plt.ylim(0, 105)
    for p in ax.patches:
        h = p.get_height()
        if h > 0:
            ax.annotate(f"{h:.1f}%", (p.get_x() + p.get_width() / 2., h / 2),
                        ha='center', va='center', color='white', fontweight='bold', fontsize=9)
    plt.tight_layout()
    plot_path1 = RESULTS_DIR / "deal_rate_comparison.png"
    plt.savefig(plot_path1, dpi=300)
    plt.close()
    print(f"Saved plot: {plot_path1}")

    # 2. Realized Payoffs by Company across Conditions
    payoff_cols = ["payoff_g_corp", "payoff_yang", "payoff_chang_liu"]
    melted = df.melt(
        id_vars=["condition_id", "model_name"],
        value_vars=payoff_cols,
        var_name="company",
        value_name="payoff"
    )
    name_map = {
        "payoff_g_corp": "G-Corp ($450k walkaway)",
        "payoff_yang": "Yang Industries ($300k walkaway)",
        "payoff_chang_liu": "Chang-Liu ($100k walkaway)",
    }
    melted["company"] = melted["company"].map(name_map)

    plt.figure(figsize=(10, 6))
    sns.boxplot(
        data=melted,
        x="condition_id",
        y="payoff",
        hue="company",
        palette="Set2"
    )
    plt.axhline(500000, color="gray", linestyle="--", alpha=0.5, label="Nash G-Corp ($500k)")
    plt.axhline(350000, color="gray", linestyle=":", alpha=0.5, label="Nash Yang ($350k)")
    plt.axhline(150000, color="gray", linestyle="-.", alpha=0.5, label="Nash Chang-Liu ($150k)")
    plt.title("Realized Payoff Distribution by Company across Governance Mechanisms", fontsize=13, fontweight="bold")
    plt.xlabel("Governance Condition", fontsize=11)
    plt.ylabel("Realized Payoff ($)", fontsize=11)
    plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0)
    plt.tight_layout()
    plot_path2 = RESULTS_DIR / "payoffs_by_company.png"
    plt.savefig(plot_path2, dpi=300)
    plt.close()
    print(f"Saved plot: {plot_path2}")


def main():
    print("=" * 70)
    print("PHASE 8: RESULTS ANALYSIS & REPORTING")
    print("=" * 70)

    try:
        df = load_results_df()
    except FileNotFoundError:
        print("No results/summary.csv found yet. Run scripts/run_pilot.py or scripts/run_experiments.py first.")
        return

    print(f"Loaded {len(df)} run records from results/summary.csv.\n")

    print("--- 1. Governance Summary Table ---")
    summary_tbl = compute_governance_summary_table(df)
    print(summary_tbl.to_string(index=False))
    print()

    print("--- 2. Mean Payoffs & Outside Option Violation Rates ---")
    payoff_tbl = compute_payoffs_table(df)
    print(payoff_tbl.to_string(index=False))
    print()

    print("--- 3. Coalition Detection & Baron-Ferejohn Exploitation ---")
    coalition_breakdown_tbl = compute_coalition_breakdown(df)
    print(coalition_breakdown_tbl.to_string(index=False))
    print()

    print("--- 4. Winning Coalition Pairs (Board Vote) ---")
    coalition_tbl = compute_coalition_frequencies(df)
    if not coalition_tbl.empty:
        print(coalition_tbl.to_string(index=False))
    else:
        print("No Board Vote runs found.")
    print()

    print("--- 5. Strategic Claim Bluffing Profile (Overall by Model) ---")
    model_honesty_tbl = compute_company_honesty_summary(df)
    print(model_honesty_tbl.to_string(index=False))
    print()

    print("--- 6. Honesty & Strategic Disclosure by Governance Condition ---")
    cond_honesty_tbl = compute_honesty_strategic_disclosure_table(df)
    # Format for clean display
    display_cond_honesty = cond_honesty_tbl.copy()
    display_cond_honesty["mean_claim"] = display_cond_honesty["mean_claim"].apply(
        lambda v: f"${v:,.0f}" if pd.notna(v) else "N/A"
    )
    display_cond_honesty["mean_inflation_ratio"] = display_cond_honesty["mean_inflation_ratio"].apply(
        lambda v: f"{v:.2f}x" if pd.notna(v) else "N/A"
    )
    print(display_cond_honesty.to_string(index=False))
    print()

    generate_plots(df)
    print("=" * 70)


if __name__ == "__main__":
    main()
