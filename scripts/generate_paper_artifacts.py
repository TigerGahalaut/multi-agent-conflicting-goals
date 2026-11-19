"""Publication Artifact Generator: Charts, Tables, and LaTeX Snippets.
Analyzes both the Homogeneous Baseline (80 runs) and the Balanced Latin Square (48 runs).
Produces publication-ready 300 DPI figures in results/plots/ and markdown tables.
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

RESULTS_DIR = Path("results")
PLOTS_DIR = RESULTS_DIR / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = RESULTS_DIR / "summary.csv"


def load_and_clean_data():
    df = pd.read_csv(CSV_PATH)
    
    # Categorize runs
    def categorize_run(row):
        rid = str(row["run_id"])
        if rid.startswith("mixed_"):
            return "Heterogeneous (Latin Square)"
        elif "gemini-3.5-flash-lite" in rid or "gemini-3.8-flash" in rid:
            return "Homogeneous (Gemini Baseline)"
        else:
            return "Homogeneous (Smoke Tests)"

    df["experiment_type"] = df.apply(categorize_run, axis=1)
    
    # Standardize condition display names
    cond_map = {
        "mbrp": "MBRP (Alternating)",
        "free": "Free Deliberation",
        "board_vote": "Board Vote (Majority)",
        "arbitrator": "Neutral Arbitrator"
    }
    df["condition_label"] = df["condition_id"].map(cond_map)
    return df


def plot_governance_efficiency(df):
    """Figure 1: Deal Rate and Surplus Realized by Condition (Homogeneous vs Heterogeneous)."""
    sns.set_theme(style="whitegrid", font_scale=1.1)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # Filter to main comparison groups
    main_df = df[df["experiment_type"].isin(["Homogeneous (Gemini Baseline)", "Heterogeneous (Latin Square)"])].copy()

    # Deal Rate
    deal_stats = main_df.groupby(["condition_label", "experiment_type"])["deal_reached"].mean().reset_index()
    deal_stats["deal_rate_pct"] = deal_stats["deal_reached"] * 100

    order = ["MBRP (Alternating)", "Free Deliberation", "Board Vote (Majority)", "Neutral Arbitrator"]

    ax1 = sns.barplot(
        data=deal_stats,
        x="condition_label",
        y="deal_rate_pct",
        hue="experiment_type",
        order=order,
        palette=["#4C72B0", "#55A868"],
        ax=axes[0]
    )
    axes[0].set_title("A. Deal Completion Rate by Governance Mechanism", fontweight="bold", pad=12)
    axes[0].set_xlabel("Governance Mechanism", fontweight="bold")
    axes[0].set_ylabel("Deal Completion Rate (%)", fontweight="bold")
    axes[0].set_ylim(0, 115)
    axes[0].legend(title="Experiment Type", loc="lower right")

    for p in ax1.patches:
        h = p.get_height()
        if h > 0:
            ax1.annotate(f"{h:.1f}%", (p.get_x() + p.get_width() / 2., h + 2),
                         ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Surplus Realized
    surplus_stats = main_df.groupby(["condition_label", "experiment_type"])["surplus_realized"].mean().reset_index()

    ax2 = sns.barplot(
        data=surplus_stats,
        x="condition_label",
        y="surplus_realized",
        hue="experiment_type",
        order=order,
        palette=["#4C72B0", "#55A868"],
        ax=axes[1]
    )
    axes[1].set_title("B. Average Realized Surplus ($150,000 Max)", fontweight="bold", pad=12)
    axes[1].set_xlabel("Governance Mechanism", fontweight="bold")
    axes[1].set_ylabel("Surplus Realized ($)", fontweight="bold")
    axes[1].set_ylim(0, 170000)
    axes[1].yaxis.set_major_formatter('${x:,.0f}')
    axes[1].legend(title="Experiment Type", loc="lower right")

    for p in ax2.patches:
        h = p.get_height()
        if h > 0:
            ax2.annotate(f"${h:,.0f}", (p.get_x() + p.get_width() / 2., h + 3000),
                         ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.tight_layout()
    out_path = PLOTS_DIR / "fig1_governance_efficiency.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated: {out_path}")


def plot_rounds_distribution(df):
    """Figure 2: Distribution of Rounds to Agreement across Governance Mechanisms."""
    sns.set_theme(style="whitegrid", font_scale=1.1)
    fig, ax = plt.subplots(figsize=(10, 5.5))

    mixed_df = df[df["experiment_type"] == "Heterogeneous (Latin Square)"].copy()
    order = ["MBRP (Alternating)", "Free Deliberation", "Neutral Arbitrator", "Board Vote (Majority)"]

    palette = {"DEAL": "#2ca02c", "DEADLOCK": "#d62728"}
    mixed_df["status"] = mixed_df["deal_reached"].map({True: "DEAL", False: "DEADLOCK"})

    sns.stripplot(
        data=mixed_df,
        x="condition_label",
        y="rounds_taken",
        hue="status",
        order=order,
        palette=palette,
        dodge=True,
        jitter=0.25,
        size=10,
        alpha=0.85,
        ax=ax
    )

    # Overlay boxplot
    sns.boxplot(
        data=mixed_df,
        x="condition_label",
        y="rounds_taken",
        order=order,
        color="lightgray",
        boxprops=dict(alpha=0.3),
        showcaps=True,
        ax=ax
    )

    ax.set_title("Deliberation Rounds to Outcome (Heterogeneous Latin Square, N=48)", fontweight="bold", pad=12)
    ax.set_xlabel("Governance Mechanism", fontweight="bold")
    ax.set_ylabel("Rounds Taken (Deadline = 8)", fontweight="bold")
    ax.set_ylim(0.5, 8.5)
    ax.axhline(8, color="red", linestyle="--", alpha=0.5, label="Deadline (Round 8)")
    ax.legend(title="Outcome", loc="upper left")

    plt.tight_layout()
    out_path = PLOTS_DIR / "fig2_rounds_distribution.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated: {out_path}")


def plot_board_vote_coalitions(df):
    """Figure 3: Baron-Ferejohn Coalitional Breakdown in Board Vote."""
    sns.set_theme(style="whitegrid", font_scale=1.1)
    fig, ax = plt.subplots(figsize=(9, 5))

    mixed_bv = df[(df["experiment_type"] == "Heterogeneous (Latin Square)") & (df["condition_id"] == "board_vote")].copy()

    coalition_counts = mixed_bv["winning_voters"].value_counts().reset_index()
    coalition_counts.columns = ["coalition", "count"]
    coalition_counts["pct"] = (coalition_counts["count"] / len(mixed_bv)) * 100

    coalition_labels = {
        "Yang Industries;Chang-Liu Cloud Services": "Yang + Chang-Liu\n('Underdog Alliance')",
        "G-Corp;Yang Industries": "G-Corp + Yang\n(IP + Manufacturer)",
        "G-Corp;Chang-Liu Cloud Services": "G-Corp + Chang-Liu\n(IP + Cloud)"
    }
    coalition_counts["clean_label"] = coalition_counts["coalition"].map(coalition_labels)

    colors = ["#d95f02", "#1b9e77", "#7570b3"]
    bars = ax.bar(coalition_counts["clean_label"], coalition_counts["count"], color=colors, width=0.55, edgecolor="black")

    ax.set_title("Winning 2-vs-1 Coalitions in Board Vote (N=12 Games)", fontweight="bold", pad=12)
    ax.set_xlabel("Majority Coalition Formed", fontweight="bold")
    ax.set_ylabel("Number of Games Passed", fontweight="bold")
    ax.set_ylim(0, 8)

    for bar, pct in zip(bars, coalition_counts["pct"]):
        h = bar.get_height()
        ax.annotate(f"{int(h)} games ({pct:.1f}%)", (bar.get_x() + bar.get_width() / 2., h + 0.2),
                    ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.tight_layout()
    out_path = PLOTS_DIR / "fig3_board_vote_coalitions.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated: {out_path}")


def plot_latin_square_model_surplus(df):
    """Figure 4: Average Payoff & Net Surplus by LLM Provider across Latin Square (N=48)."""
    sns.set_theme(style="whitegrid", font_scale=1.1)
    fig, ax = plt.subplots(figsize=(9, 5.5))

    mixed_df = df[df["experiment_type"] == "Heterogeneous (Latin Square)"].copy()

    records = []
    for _, row in mixed_df.iterrows():
        tokens = str(row["run_id"]).split("_")
        try:
            idx = int(tokens[-1])
        except Exception:
            continue
        shift = (idx - 1) % 3

        p_g = float(row["payoff_g_corp"])
        p_y = float(row["payoff_yang"])
        p_c = float(row["payoff_chang_liu"])

        if shift == 0:
            records.append({"model": "Claude Haiku 5.5", "provider": "Anthropic", "payoff": p_g, "role": "G-Corp", "walkaway": 450000})
            records.append({"model": "GPT-6 Luna", "provider": "OpenAI", "payoff": p_y, "role": "Yang", "walkaway": 300000})
            records.append({"model": "Gemini 3.8 Flash", "provider": "Google", "payoff": p_c, "role": "Chang-Liu", "walkaway": 100000})
        elif shift == 1:
            records.append({"model": "GPT-6 Luna", "provider": "OpenAI", "payoff": p_g, "role": "G-Corp", "walkaway": 450000})
            records.append({"model": "Gemini 3.8 Flash", "provider": "Google", "payoff": p_y, "role": "Yang", "walkaway": 300000})
            records.append({"model": "Claude Haiku 5.5", "provider": "Anthropic", "payoff": p_c, "role": "Chang-Liu", "walkaway": 100000})
        elif shift == 2:
            records.append({"model": "Gemini 3.8 Flash", "provider": "Google", "payoff": p_g, "role": "G-Corp", "walkaway": 450000})
            records.append({"model": "Claude Haiku 5.5", "provider": "Anthropic", "payoff": p_y, "role": "Yang", "walkaway": 300000})
            records.append({"model": "GPT-6 Luna", "provider": "OpenAI", "payoff": p_c, "role": "Chang-Liu", "walkaway": 100000})

    m_df = pd.DataFrame(records)
    m_df["surplus_extracted"] = m_df["payoff"] - m_df["walkaway"]

    summary = m_df.groupby("model").agg(
        avg_payoff=("payoff", "mean"),
        avg_surplus=("surplus_extracted", "mean"),
        count=("payoff", "count")
    ).reset_index()

    order = ["Gemini 3.8 Flash", "GPT-6 Luna", "Claude Haiku 5.5"]
    summary = summary.set_index("model").loc[order].reset_index()

    colors = ["#4285F4", "#10A37F", "#CC785C"]
    bars = ax.bar(summary["model"], summary["avg_surplus"], color=colors, width=0.5, edgecolor="black")

    ax.set_title("Normalized Surplus Extracted by LLM Provider (Latin Square N=48)", fontweight="bold", pad=12)
    ax.set_xlabel("LLM Provider / Model", fontweight="bold")
    ax.set_ylabel("Average Net Surplus Extracted Above Outside Option ($)", fontweight="bold")
    ax.yaxis.set_major_formatter('${x:,.0f}')
    ax.set_ylim(0, 65000)

    for bar, p_val in zip(bars, summary["avg_payoff"]):
        h = bar.get_height()
        ax.annotate(f"+${h:,.0f}\n(Avg Payoff: ${p_val:,.0f})", 
                    (bar.get_x() + bar.get_width() / 2., h + 1500),
                    ha='center', va='bottom', fontsize=9.5, fontweight='bold')

    plt.tight_layout()
    out_path = PLOTS_DIR / "fig4_latin_square_model_surplus.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated: {out_path}")


def print_latex_tables(df):
    """Prints publication-ready Markdown/LaTeX tables."""
    print("\n" + "="*70)
    print("TABLE 1: GOVERNANCE MECHANISM COMPARISON (HETEROGENEOUS LATIN SQUARE)")
    print("="*70)
    mixed_df = df[df["experiment_type"] == "Heterogeneous (Latin Square)"].copy()
    t1 = mixed_df.groupby("condition_id").agg(
        runs=("deal_reached", "count"),
        deals=("deal_reached", "sum"),
        deal_rate=("deal_reached", lambda x: f"{x.mean()*100:.1f}%"),
        avg_rounds=("rounds_taken", lambda x: f"{x.mean():.1f}"),
        avg_surplus=("surplus_realized", lambda x: f"${x.mean():,.0f}"),
        avg_nash_dist=("nash_distance", lambda x: f"${pd.to_numeric(x, errors='coerce').mean():,.0f}"),
        g_corp=("payoff_g_corp", lambda x: f"${x.mean():,.0f}"),
        yang=("payoff_yang", lambda x: f"${x.mean():,.0f}"),
        chang_liu=("payoff_chang_liu", lambda x: f"${x.mean():,.0f}"),
    ).loc[["mbrp", "free", "board_vote", "arbitrator"]].reset_index()

    print(t1.to_markdown(index=False))


def main():
    print("="*70)
    print("GENERATING PUBLICATION ARTIFACTS (PLOTS & TABLES)")
    print("="*70)
    df = load_and_clean_data()
    print(f"Loaded {len(df)} total negotiation runs.")
    
    plot_governance_efficiency(df)
    plot_rounds_distribution(df)
    plot_board_vote_coalitions(df)
    plot_latin_square_model_surplus(df)
    print_latex_tables(df)
    print("\nAll publication artifacts generated successfully in results/plots/!")


if __name__ == "__main__":
    main()
