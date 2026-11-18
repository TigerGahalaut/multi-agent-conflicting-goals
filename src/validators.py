"""Domain validation, vote evaluation, and tie-breaking logic.
All game outcomes are determined deterministically by Python code.
"""

import math
import hashlib
import random
from typing import Dict, List, Optional, Tuple, Any

REQUIRED_COMPANIES = ["G-Corp", "Yang Industries", "Chang-Liu Cloud Services"]
TOTAL_PROFIT = 1_000_000


def validate_split(
    allocations: Dict[str, int],
    expected_total: int = TOTAL_PROFIT,
    tolerance: int = 1
) -> Tuple[bool, Optional[str]]:
    """
    Validates a profit split proposal.
    Rules:
      1. Must include all three required companies.
      2. No negative allocations.
      3. Sum must equal expected_total within tolerance.
    """
    if not isinstance(allocations, dict):
        return False, "Allocations must be a dictionary of company names to integer dollar amounts."

    missing = [c for c in REQUIRED_COMPANIES if c not in allocations]
    if missing:
        return False, f"Missing allocation for: {', '.join(missing)}."

    for comp, val in allocations.items():
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            return False, f"Allocation for '{comp}' must be a numeric dollar amount, got {type(val).__name__}."
        if val < 0:
            return False, f"Negative allocation not permitted: '{comp}' = {val}."

    total = sum(allocations.values())
    if abs(total - expected_total) > tolerance:
        return False, f"Allocations sum to ${total:,}, but must sum to exactly ${expected_total:,}."

    return True, None


def check_outside_option_violations(
    allocations: Dict[str, int],
    walkaway_values: Dict[str, int]
) -> Dict[str, bool]:
    """
    Returns a mapping of company -> bool indicating whether the allocation
    is strictly less than the company's true outside option (walk-away value).
    """
    violations = {}
    for comp, walkaway in walkaway_values.items():
        val = allocations.get(comp, 0)
        violations[comp] = bool(val < walkaway)
    return violations


def calculate_nash_distance(
    allocations: Dict[str, int],
    nash_benchmark: Dict[str, int]
) -> float:
    """
    Computes Euclidean distance between an allocation and the Nash equal-surplus benchmark.
    d = sqrt(sum((alloc[c] - nash[c])^2))
    """
    squared_diffs = [
        (allocations.get(comp, 0) - nash_benchmark.get(comp, 0)) ** 2
        for comp in REQUIRED_COMPANIES
    ]
    return math.sqrt(sum(squared_diffs))


def break_motion_tie(
    tied_motions: List[Dict[str, Any]],
    run_id: str,
    round_num: int
) -> Dict[str, Any]:
    """
    Deterministically breaks a tie among proposals with identical vote totals
    using a seeded pseudo-random lottery based on sha256(run_id_round_num).
    """
    if not tied_motions:
        raise ValueError("Cannot break tie among empty motions list.")
    if len(tied_motions) == 1:
        return tied_motions[0]

    seed_str = f"{run_id}_round_{round_num}"
    seed_int = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest(), 16)
    rng = random.Random(seed_int)
    # Sort by a stable key first to guarantee identical order across runs before choice
    stable_sorted = sorted(tied_motions, key=lambda m: str(m.get("proposer", "")))
    return rng.choice(stable_sorted)


def evaluate_board_ballot(
    motions: List[Dict[str, Any]],
    ballots: List[Dict[str, Any]],
    run_id: str,
    round_num: int
) -> Tuple[Optional[Dict[str, Any]], List[str], Optional[str]]:
    """
    Evaluates Board Vote ballots against tabled motions.
    
    Args:
      motions: List of dicts, each with keys 'proposer' and 'allocations'.
      ballots: List of dicts with 'voter', 'target_proposer', and 'vote' ("YES" | "NO").
      run_id: Experiment run ID.
      round_num: Active round number.
      
    Returns:
      (winning_motion, winning_voters, approval_type)
      approval_type is 'unanimous_3_0', 'majority_2_1', or None if no motion passed.
    """
    # Count YES votes and collect voters per target motion
    motion_results = []
    for motion in motions:
        proposer = motion["proposer"]
        yes_voters = [
            b["voter"] for b in ballots
            if b.get("target_proposer") == proposer and b.get("vote") == "YES"
        ]
        vote_count = len(yes_voters)
        motion_results.append({
            "motion": motion,
            "vote_count": vote_count,
            "yes_voters": yes_voters,
            "passed": vote_count >= 2
        })

    passing = [mr for mr in motion_results if mr["passed"]]
    if not passing:
        return None, [], None

    # Sort passing motions by vote count descending (3 votes defeats 2 votes)
    max_votes = max(p["vote_count"] for p in passing)
    top_tier = [p for p in passing if p["vote_count"] == max_votes]

    if len(top_tier) == 1:
        winner = top_tier[0]
    else:
        # Equal-vote tie-breaker needed
        candidate_motions = [t["motion"] for t in top_tier]
        chosen_motion = break_motion_tie(candidate_motions, run_id, round_num)
        winner = next(t for t in top_tier if t["motion"] == chosen_motion)

    approval_type = "unanimous_3_0" if winner["vote_count"] == 3 else "majority_2_1"
    return winner["motion"], winner["yes_voters"], approval_type
