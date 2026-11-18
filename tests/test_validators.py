"""Unit tests for split validation, vote evaluation, and tie-breaking."""

import pytest
from src.validators import (
    validate_split,
    check_outside_option_violations,
    calculate_nash_distance,
    break_motion_tie,
    evaluate_board_ballot,
    TOTAL_PROFIT
)

WALKAWAY = {
    "G-Corp": 450000,
    "Yang Industries": 300000,
    "Chang-Liu Cloud Services": 100000
}

NASH_BENCHMARK = {
    "G-Corp": 500000,
    "Yang Industries": 350000,
    "Chang-Liu Cloud Services": 150000
}


def test_validate_split_valid():
    valid_alloc = {
        "G-Corp": 500000,
        "Yang Industries": 350000,
        "Chang-Liu Cloud Services": 150000
    }
    is_valid, err = validate_split(valid_alloc)
    assert is_valid is True
    assert err is None


def test_validate_split_wrong_sum():
    bad_sum = {
        "G-Corp": 500000,
        "Yang Industries": 300000,
        "Chang-Liu Cloud Services": 100000  # Sums to 900,000
    }
    is_valid, err = validate_split(bad_sum)
    assert is_valid is False
    assert "must sum to exactly $1,000,000" in err


def test_validate_split_negative_value():
    neg_alloc = {
        "G-Corp": 700000,
        "Yang Industries": 350000,
        "Chang-Liu Cloud Services": -50000
    }
    is_valid, err = validate_split(neg_alloc)
    assert is_valid is False
    assert "Negative allocation" in err


def test_validate_split_missing_company():
    missing_alloc = {
        "G-Corp": 600000,
        "Yang Industries": 400000
    }
    is_valid, err = validate_split(missing_alloc)
    assert is_valid is False
    assert "Missing allocation for: Chang-Liu Cloud Services" in err


def test_outside_option_violations():
    # G-Corp gets 400,000 (< 450,000 walkaway)
    alloc = {
        "G-Corp": 400000,
        "Yang Industries": 400000,
        "Chang-Liu Cloud Services": 200000
    }
    violations = check_outside_option_violations(alloc, WALKAWAY)
    assert violations["G-Corp"] is True
    assert violations["Yang Industries"] is False
    assert violations["Chang-Liu Cloud Services"] is False


def test_nash_distance():
    # Exact Nash split -> distance is 0.0
    dist_zero = calculate_nash_distance(NASH_BENCHMARK, NASH_BENCHMARK)
    assert dist_zero == 0.0

    # Perturbed split: G-Corp +10,000, Chang-Liu -10,000
    perturbed = {
        "G-Corp": 510000,
        "Yang Industries": 350000,
        "Chang-Liu Cloud Services": 140000
    }
    # sqrt(10000^2 + 0 + (-10000)^2) = sqrt(200,000,000) ~= 14142.1356
    dist = calculate_nash_distance(perturbed, NASH_BENCHMARK)
    assert round(dist, 2) == 14142.14


def test_break_motion_tie_deterministic():
    motions = [
        {"proposer": "G-Corp", "allocations": {"G-Corp": 600000, "Yang Industries": 400000, "Chang-Liu Cloud Services": 0}},
        {"proposer": "Yang Industries", "allocations": {"G-Corp": 0, "Yang Industries": 600000, "Chang-Liu Cloud Services": 400000}}
    ]
    # Same run_id and round must yield identical choice every time
    choice1 = break_motion_tie(motions, run_id="run_test_01", round_num=3)
    choice2 = break_motion_tie(motions, run_id="run_test_01", round_num=3)
    assert choice1 == choice2


def test_evaluate_board_ballot_unanimous_beats_majority():
    m1 = {"proposer": "G-Corp", "allocations": {"G-Corp": 500000, "Yang Industries": 350000, "Chang-Liu Cloud Services": 150000}}
    m2 = {"proposer": "Yang Industries", "allocations": {"G-Corp": 400000, "Yang Industries": 450000, "Chang-Liu Cloud Services": 150000}}
    motions = [m1, m2]

    # m1 gets 3 YES votes, m2 gets 2 YES votes
    ballots = [
        {"voter": "G-Corp", "target_proposer": "G-Corp", "vote": "YES"},
        {"voter": "Yang Industries", "target_proposer": "G-Corp", "vote": "YES"},
        {"voter": "Chang-Liu Cloud Services", "target_proposer": "G-Corp", "vote": "YES"},
        {"voter": "G-Corp", "target_proposer": "Yang Industries", "vote": "NO"},
        {"voter": "Yang Industries", "target_proposer": "Yang Industries", "vote": "YES"},
        {"voter": "Chang-Liu Cloud Services", "target_proposer": "Yang Industries", "vote": "YES"},
    ]

    winner, voters, approval_type = evaluate_board_ballot(motions, ballots, run_id="run_1", round_num=1)
    assert winner == m1
    assert set(voters) == {"G-Corp", "Yang Industries", "Chang-Liu Cloud Services"}
    assert approval_type == "unanimous_3_0"


def test_evaluate_board_ballot_minimum_winning_coalition():
    m1 = {"proposer": "G-Corp", "allocations": {"G-Corp": 550000, "Yang Industries": 450000, "Chang-Liu Cloud Services": 0}}
    motions = [m1]

    # G-Corp and Yang vote YES; Chang-Liu votes NO
    ballots = [
        {"voter": "G-Corp", "target_proposer": "G-Corp", "vote": "YES"},
        {"voter": "Yang Industries", "target_proposer": "G-Corp", "vote": "YES"},
        {"voter": "Chang-Liu Cloud Services", "target_proposer": "G-Corp", "vote": "NO"},
    ]

    winner, voters, approval_type = evaluate_board_ballot(motions, ballots, run_id="run_1", round_num=1)
    assert winner == m1
    assert set(voters) == {"G-Corp", "Yang Industries"}
    assert approval_type == "majority_2_1"


def test_evaluate_board_ballot_no_pass():
    m1 = {"proposer": "G-Corp", "allocations": {"G-Corp": 800000, "Yang Industries": 100000, "Chang-Liu Cloud Services": 100000}}
    motions = [m1]

    # Only G-Corp votes YES; both others vote NO
    ballots = [
        {"voter": "G-Corp", "target_proposer": "G-Corp", "vote": "YES"},
        {"voter": "Yang Industries", "target_proposer": "G-Corp", "vote": "NO"},
        {"voter": "Chang-Liu Cloud Services", "target_proposer": "G-Corp", "vote": "NO"},
    ]

    winner, voters, approval_type = evaluate_board_ballot(motions, ballots, run_id="run_1", round_num=1)
    assert winner is None
    assert voters == []
    assert approval_type is None
