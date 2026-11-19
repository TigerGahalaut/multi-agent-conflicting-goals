import pandas as pd
import numpy as np

df = pd.read_csv("results/summary.csv")

# Filter for mixed runs only
mixed_df = df[df["run_id"].str.startswith("mixed_")].copy()
print(f"Total Mixed Games Found: {len(mixed_df)}")

# Summary by condition
print("\n" + "="*60)
print("GOVERNANCE CONDITION PERFORMANCE (MIXED-MODEL)")
print("="*60)
cond_summary = mixed_df.groupby("condition_id").agg(
    total_runs=("deal_reached", "count"),
    deal_rate=("deal_reached", lambda x: f"{x.mean()*100:.1f}%"),
    avg_rounds=("rounds_taken", "mean"),
    avg_surplus=("surplus_realized", "mean"),
    avg_nash_dist=("nash_distance", lambda x: f"{pd.to_numeric(x, errors='coerce').mean():.1f}"),
    violations=("below_walkaway_accepted", lambda x: (x == True).sum() + (mixed_df.loc[x.index, "violation_g_corp"] == True).sum())
).reset_index()
print(cond_summary.to_string(index=False))

# Board Vote Coalitions
print("\n" + "="*60)
print("BOARD VOTE COALITIONAL DYNAMICS")
print("="*60)
bv = mixed_df[mixed_df["condition_id"] == "board_vote"]
print("Winning Coalitions:")
print(bv["winning_voters"].value_counts())
print("\nOutvoted Firm Bound (Squeezed):")
print(bv["squeezed_firm"].value_counts(dropna=False))

# Profit breakdown by company and condition
print("\n" + "="*60)
print("AVERAGE PAYOFFS BY CONDITION ($)")
print("="*60)
payoffs = mixed_df.groupby("condition_id").agg(
    g_corp=("payoff_g_corp", "mean"),
    yang=("payoff_yang", "mean"),
    chang_liu=("payoff_chang_liu", "mean"),
    total=("surplus_realized", lambda s: s.mean() + 850000)
).reset_index()
print(payoffs.to_string(index=False))
