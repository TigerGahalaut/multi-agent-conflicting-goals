"""Phase 6: Single-run pilot runner and token/cost audit across all 3 conditions.
Runs 1 pilot negotiation per condition on the baseline model to verify the live API,
measure token consumption, and extrapolate total experimental costs before launching the full matrix.
"""

import sys
import os
import time

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.orchestrator import run_single_negotiation

# Gemini 3.5 Flash-Lite estimated pricing (per million tokens)
PRICE_PER_M_PROMPT = 0.075
PRICE_PER_M_CANDIDATE = 0.300


def main():
    print("=" * 70)
    print("PHASE 6 PILOT: Running 1 Live Negotiation per Governance Condition")
    print("Model: gemini-3.5-flash-lite | Thinking: MINIMAL")
    print("=" * 70)

    conditions = ["mbrp", "board_vote", "arbitrator"]
    pilot_results = []
    total_prompt_tokens = 0
    total_candidate_tokens = 0

    for idx, cond in enumerate(conditions):
        run_id = f"pilot_{cond}_{int(time.time())}"
        print(f"\n[Pilot {idx + 1}/3] Starting Condition: {cond.upper()} (Run ID: {run_id})...")
        t0 = time.time()
        res = run_single_negotiation(
            run_id=run_id,
            condition_id=cond,
            model_name="gemini-3.5-flash-lite",
            thinking_level="MINIMAL",
            run_index=0,
            max_rounds=8,
        )
        elapsed = time.time() - t0

        tokens = res.token_usage
        total_prompt_tokens += tokens.get("prompt_tokens", 0)
        total_candidate_tokens += tokens.get("candidate_tokens", 0)

        pilot_results.append({
            "condition": cond,
            "deal_reached": res.deal_reached,
            "rounds_taken": res.rounds_taken,
            "approval_type": res.approval_type,
            "agreed_allocation": res.agreed_allocation,
            "prompt_tokens": tokens.get("prompt_tokens", 0),
            "candidate_tokens": tokens.get("candidate_tokens", 0),
            "total_tokens": tokens.get("total_tokens", 0),
            "elapsed_seconds": round(elapsed, 1),
        })

        status = "DEAL" if res.deal_reached else "DEADLOCK"
        print(f" -> Result: {status} in Round {res.rounds_taken} ({elapsed:.1f}s)")
        print(f" -> Agreed split: {res.agreed_allocation}")
        print(f" -> Tokens: {tokens.get('prompt_tokens', 0)} prompt + {tokens.get('candidate_tokens', 0)} candidate = {tokens.get('total_tokens', 0)} total")

    print("\n" + "=" * 70)
    print("PILOT AUDIT & 60-RUN BUDGET PROJECTION")
    print("=" * 70)

    pilot_cost = (
        (total_prompt_tokens / 1_000_000) * PRICE_PER_M_PROMPT +
        (total_candidate_tokens / 1_000_000) * PRICE_PER_M_CANDIDATE
    )
    avg_tokens_per_run = (total_prompt_tokens + total_candidate_tokens) / len(conditions)
    avg_cost_per_run = pilot_cost / len(conditions)

    # 60 total runs (30 Tier A @ flash-lite rates, 30 Tier B @ flash rates ~2.5x)
    est_60_run_cost_tier_a = avg_cost_per_run * 30
    est_60_run_cost_tier_b = (avg_cost_per_run * 2.5) * 30
    projected_total_cost = est_60_run_cost_tier_a + est_60_run_cost_tier_b

    print(f"Total pilot tokens consumed (3 runs): {total_prompt_tokens + total_candidate_tokens:,}")
    print(f"Total pilot cost (3 runs):             ${pilot_cost:.5f}")
    print(f"Average cost per negotiation:          ${avg_cost_per_run:.5f}")
    print(f"Average tokens per negotiation:        {avg_tokens_per_run:,.0f}")
    print("-" * 70)
    print(f"Projected cost for full 60-run matrix: ${projected_total_cost:.2f}")
    print(f"Available GCP promotional credit:      $50.00")
    print(f"Budget headroom:                       ${50.00 - projected_total_cost:.2f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
