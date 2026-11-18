"""Unit tests for metrics and analysis calculations."""

import pytest
import pandas as pd
from src.metrics import (
    compute_governance_summary_table,
    compute_payoffs_table,
    compute_coalition_breakdown,
    compute_coalition_frequencies,
    compute_honesty_strategic_disclosure_table,
    compute_company_honesty_summary,
)


@pytest.fixture
def sample_results_df():
    data = [
        {
            "run_id": "test_bv_1",
            "condition_id": "board_vote",
            "model_name": "gemini-3.5-flash-lite",
            "deal_reached": True,
            "rounds_taken": 3,
            "surplus_realized": 150000,
            "approval_type": "majority_2_1",
            "winning_voters": "Yang Industries;Chang-Liu Cloud Services",
            "payoff_g_corp": 333000,
            "payoff_yang": 333000,
            "payoff_chang_liu": 334000,
            "violation_g_corp": True,
            "violation_yang": False,
            "violation_chang_liu": False,
            "nash_distance": 249066.26,
            "two_vs_one_nash": False,
            "squeezed_firm": "",
            "outvoted_firm_bound": True,
            "below_walkaway_imposed": True,
            "imposed_on": "G-Corp",
            "below_walkaway_accepted": False,
            "first_claim_g_corp": 450000,
            "first_claim_yang": 300000,
            "first_claim_chang_liu": 200000,
            "inflation_ratio_g_corp": 1.0,
            "inflation_ratio_yang": 1.0,
            "inflation_ratio_chang_liu": 2.0,
        },
        {
            "run_id": "test_arb_1",
            "condition_id": "arbitrator",
            "model_name": "gemini-3.5-flash-lite",
            "deal_reached": True,
            "rounds_taken": 2,
            "surplus_realized": 150000,
            "approval_type": "unanimous_3_0",
            "winning_voters": "G-Corp;Yang Industries;Chang-Liu Cloud Services",
            "payoff_g_corp": 500000,
            "payoff_yang": 350000,
            "payoff_chang_liu": 150000,
            "violation_g_corp": False,
            "violation_yang": False,
            "violation_chang_liu": False,
            "nash_distance": 0.0,
            "two_vs_one_nash": False,
            "squeezed_firm": "",
            "outvoted_firm_bound": False,
            "below_walkaway_imposed": False,
            "imposed_on": "",
            "below_walkaway_accepted": False,
            "first_claim_g_corp": 450000,
            "first_claim_yang": 300000,
            "first_claim_chang_liu": None,
            "inflation_ratio_g_corp": 1.0,
            "inflation_ratio_yang": 1.0,
            "inflation_ratio_chang_liu": None,
        },
    ]
    return pd.DataFrame(data)


def test_compute_coalition_breakdown(sample_results_df):
    breakdown = compute_coalition_breakdown(sample_results_df)
    assert len(breakdown) == 2
    bv_row = breakdown[breakdown["condition_id"] == "board_vote"].iloc[0]
    assert bv_row["outvoted_bound"] == 1
    assert bv_row["below_walkaway_imposed"] == 1
    assert bv_row["imposed_loss_rate_pct"] == 100.0


def test_compute_honesty_strategic_disclosure(sample_results_df):
    disc = compute_honesty_strategic_disclosure_table(sample_results_df)
    assert len(disc) == 6  # 2 conditions x 3 companies
    cl_bv = disc[(disc["condition_id"] == "board_vote") & (disc["company"] == "Chang-Liu Cloud Services")].iloc[0]
    assert cl_bv["disclosure_rate_pct"] == 100.0
    assert cl_bv["mean_claim"] == 200000.0
    assert cl_bv["mean_inflation_ratio"] == 2.0


def test_compute_company_honesty_summary(sample_results_df):
    summary = compute_company_honesty_summary(sample_results_df)
    assert len(summary) == 3  # 1 model x 3 companies
    cl_row = summary[summary["company"] == "Chang-Liu Cloud Services"].iloc[0]
    assert cl_row["disclosure_count"] == "1/2"
    assert cl_row["disclosure_rate_pct"] == 50.0
    assert cl_row["mean_claim"] == 200000.0
    assert cl_row["mean_inflation_ratio"] == 2.0
