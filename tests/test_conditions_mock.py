"""Zero-cost deterministic mock tests for all three governance conditions."""

import pytest
from typing import Dict, List, Optional
from unittest.mock import MagicMock

from src.schemas import CompanyAgentResponse, ArbitratorResponse, Proposal
from src.conditions.mbrp import MBRPNegotiation
from src.conditions.board_vote import BoardVoteNegotiation
from src.conditions.arbitrator import ArbitratorNegotiation
from src.validators import REQUIRED_COMPANIES


def create_mock_company_agent(name: str, walkaway: int, responses: List[CompanyAgentResponse]):
    """Creates a mock NegotiationAgent returning a predefined sequence of responses."""
    agent = MagicMock()
    agent.company_name = name
    agent.walkaway = walkaway
    agent.model_name = "mock-model"
    agent.thinking_level = "MINIMAL"
    resp_iter = iter(responses)
    
    def side_effect(*args, **kwargs):
        try:
            return next(resp_iter), {"prompt_tokens": 10, "candidate_tokens": 5, "total_tokens": 15, "model_version": "mock-v1"}
        except StopIteration:
            # Default fallback if loop exceeds responses
            return CompanyAgentResponse(
                reasoning="default",
                public_message="default message",
                claimed_walkaway=walkaway,
                vote="REJECT",
                counter_proposal=Proposal(allocations={"G-Corp": 500000, "Yang Industries": 350000, "Chang-Liu Cloud Services": 150000})
            ), {"prompt_tokens": 10, "candidate_tokens": 5, "total_tokens": 15}

    agent.generate_response.side_effect = side_effect
    return agent


def create_mock_arbitrator_agent(responses: List[ArbitratorResponse]):
    """Creates a mock ArbitratorAgent returning a predefined sequence of responses."""
    arb = MagicMock()
    arb.model_name = "mock-model"
    arb.thinking_level = "MINIMAL"
    resp_iter = iter(responses)

    def side_effect(*args, **kwargs):
        try:
            return next(resp_iter), {"prompt_tokens": 15, "candidate_tokens": 10, "total_tokens": 25, "model_version": "mock-v1"}
        except StopIteration:
            return ArbitratorResponse(
                reasoning="default",
                public_explanation="default split",
                proposed_split=Proposal(allocations={"G-Corp": 500000, "Yang Industries": 350000, "Chang-Liu Cloud Services": 150000})
            ), {"prompt_tokens": 15, "candidate_tokens": 10, "total_tokens": 25}

    arb.generate_response.side_effect = side_effect
    return arb


# -----------------------------------------------------------------------------
# MBRP Tests
# -----------------------------------------------------------------------------

def test_mbrp_round_1_unanimous_deal():
    """Tests MBRP where proposer tables Nash split and both responders accept in round 1."""
    nash_split = Proposal(allocations={"G-Corp": 500000, "Yang Industries": 350000, "Chang-Liu Cloud Services": 150000})

    # Run index 0 -> G-Corp starts as proposer
    g_corp = create_mock_company_agent("G-Corp", 450000, [
        CompanyAgentResponse(reasoning="Propose fair split", public_message="Offering Nash split", claimed_walkaway=450000, vote="ACCEPT", counter_proposal=nash_split)
    ])
    yang = create_mock_company_agent("Yang Industries", 300000, [
        CompanyAgentResponse(reasoning="Good deal", public_message="I accept", claimed_walkaway=300000, vote="ACCEPT")
    ])
    chang_liu = create_mock_company_agent("Chang-Liu Cloud Services", 100000, [
        CompanyAgentResponse(reasoning="Good deal", public_message="I accept", claimed_walkaway=100000, vote="ACCEPT")
    ])

    agents = {"G-Corp": g_corp, "Yang Industries": yang, "Chang-Liu Cloud Services": chang_liu}
    sim = MBRPNegotiation(run_id="mock_mbrp_01", run_index=0, agents=agents, model_name="mock-model", thinking_level="MINIMAL")
    res = sim.execute()

    assert res.deal_reached is True
    assert res.rounds_taken == 1
    assert res.agreed_allocation == nash_split.allocations
    assert res.surplus_realized == 150000
    assert res.approval_type == "unanimous_3_0"
    assert res.nash_distance == 0.0


def test_mbrp_deadlock_timeout():
    """Tests MBRP where responders reject every round, terminating at Round 8."""
    greedy_split = Proposal(allocations={"G-Corp": 800000, "Yang Industries": 100000, "Chang-Liu Cloud Services": 100000})

    # Responders reject constantly
    def reject_responses():
        return [
            CompanyAgentResponse(reasoning="rejection", public_message="Unacceptable", claimed_walkaway=None, vote="REJECT", counter_proposal=greedy_split)
            for _ in range(16)
        ]

    agents = {
        "G-Corp": create_mock_company_agent("G-Corp", 450000, reject_responses()),
        "Yang Industries": create_mock_company_agent("Yang Industries", 300000, reject_responses()),
        "Chang-Liu Cloud Services": create_mock_company_agent("Chang-Liu Cloud Services", 100000, reject_responses())
    }

    sim = MBRPNegotiation(run_id="mock_mbrp_deadlock", run_index=0, agents=agents, model_name="mock-model", thinking_level="MINIMAL")
    res = sim.execute()

    assert res.deal_reached is False
    assert res.rounds_taken == 8
    assert res.agreed_allocation is None
    assert res.surplus_realized == 0
    # Walk-away outside options awarded
    assert res.realized_payoff == {"G-Corp": 450000, "Yang Industries": 300000, "Chang-Liu Cloud Services": 100000}


# -----------------------------------------------------------------------------
# Board Vote Tests
# -----------------------------------------------------------------------------

def test_board_vote_minimum_winning_coalition():
    """Tests Board Vote where G-Corp and Yang form a 2-1 coalition excluding Chang-Liu below walkaway."""
    coalition_split = Proposal(allocations={"G-Corp": 550000, "Yang Industries": 450000, "Chang-Liu Cloud Services": 0})

    # Stage 1 (Signal), Stage 2 (Motion), Stage 3 (Ballot)
    g_corp = create_mock_company_agent("G-Corp", 450000, [
        CompanyAgentResponse(reasoning="Signal to Yang", public_message="Yang, let's partner and split 550/450", claimed_walkaway=450000),
        CompanyAgentResponse(reasoning="Table motion", public_message="Tabled motion", counter_proposal=coalition_split),
        CompanyAgentResponse(reasoning="Vote on G-Corp motion", public_message="G-Corp motion: YES; others: NO", ballot={"G-Corp": "YES", "Yang Industries": "NO", "Chang-Liu Cloud Services": "NO"})
    ])
    yang = create_mock_company_agent("Yang Industries", 300000, [
        CompanyAgentResponse(reasoning="Signal agreed", public_message="G-Corp, deal agreed", claimed_walkaway=300000),
        CompanyAgentResponse(reasoning="Table motion", public_message="Yang motion", counter_proposal=coalition_split),
        CompanyAgentResponse(reasoning="Vote on G-Corp motion", public_message="G-Corp motion: YES; others: NO", ballot={"G-Corp": "YES", "Yang Industries": "NO", "Chang-Liu Cloud Services": "NO"})
    ])
    chang_liu = create_mock_company_agent("Chang-Liu Cloud Services", 100000, [
        CompanyAgentResponse(reasoning="Protest", public_message="I protest any split giving me 0", claimed_walkaway=100000),
        CompanyAgentResponse(reasoning="Fair motion", public_message="My motion", counter_proposal=Proposal(allocations={"G-Corp": 450000, "Yang Industries": 300000, "Chang-Liu Cloud Services": 250000})),
        CompanyAgentResponse(reasoning="Vote NO on G-Corp", public_message="Vote NO on coalition", ballot={"G-Corp": "NO", "Yang Industries": "NO", "Chang-Liu Cloud Services": "YES"})
    ])

    agents = {"G-Corp": g_corp, "Yang Industries": yang, "Chang-Liu Cloud Services": chang_liu}
    sim = BoardVoteNegotiation(run_id="mock_board_coalition", agents=agents, model_name="mock-model", thinking_level="MINIMAL")
    res = sim.execute()

    assert res.deal_reached is True
    assert res.rounds_taken == 1
    assert res.agreed_allocation == coalition_split.allocations
    assert res.approval_type == "majority_2_1"
    assert set(res.winning_voters) == {"G-Corp", "Yang Industries"}
    # Chang-Liu received 0 (< 100,000 walkaway), so outside option violation is flagged
    assert res.outside_option_violations["Chang-Liu Cloud Services"] is True
    assert res.outside_option_violations["G-Corp"] is False


# -----------------------------------------------------------------------------
# Arbitrator Tests
# -----------------------------------------------------------------------------

def test_arbitrator_reject_then_accept():
    """Tests Arbitrator condition where round 1 is rejected, feedback is provided, and round 2 is ratified."""
    award_r1 = Proposal(allocations={"G-Corp": 600000, "Yang Industries": 300000, "Chang-Liu Cloud Services": 100000})
    award_r2 = Proposal(allocations={"G-Corp": 500000, "Yang Industries": 350000, "Chang-Liu Cloud Services": 150000})

    arb = create_mock_arbitrator_agent([
        ArbitratorResponse(reasoning="r1 proposal", public_explanation="award 1", proposed_split=award_r1),
        ArbitratorResponse(reasoning="revised proposal after feedback", public_explanation="award 2 (revised)", proposed_split=award_r2)
    ])

    # Round 1: Chang-Liu rejects because it got 100k
    # Round 2: Everyone accepts award 2
    g_corp = create_mock_company_agent("G-Corp", 450000, [
        CompanyAgentResponse(reasoning="c1", public_message="claim 500k", claimed_walkaway=500000),
        CompanyAgentResponse(reasoning="vote 1", public_message="accept r1", vote="ACCEPT"),
        CompanyAgentResponse(reasoning="c2", public_message="claim 500k", claimed_walkaway=500000),
        CompanyAgentResponse(reasoning="vote 2", public_message="accept r2", vote="ACCEPT"),
    ])
    yang = create_mock_company_agent("Yang Industries", 300000, [
        CompanyAgentResponse(reasoning="c1", public_message="claim 350k", claimed_walkaway=350000),
        CompanyAgentResponse(reasoning="vote 1", public_message="accept r1", vote="ACCEPT"),
        CompanyAgentResponse(reasoning="c2", public_message="claim 350k", claimed_walkaway=350000),
        CompanyAgentResponse(reasoning="vote 2", public_message="accept r2", vote="ACCEPT"),
    ])
    chang_liu = create_mock_company_agent("Chang-Liu Cloud Services", 100000, [
        CompanyAgentResponse(reasoning="c1", public_message="claim 200k", claimed_walkaway=200000),
        CompanyAgentResponse(reasoning="vote 1", public_message="reject r1, I got only walkaway", vote="REJECT"),
        CompanyAgentResponse(reasoning="c2", public_message="claim 200k", claimed_walkaway=200000),
        CompanyAgentResponse(reasoning="vote 2", public_message="accept r2", vote="ACCEPT"),
    ])

    agents = {"G-Corp": g_corp, "Yang Industries": yang, "Chang-Liu Cloud Services": chang_liu}
    sim = ArbitratorNegotiation(run_id="mock_arb_flow", agents=agents, arbitrator=arb, model_name="mock-model", thinking_level="MINIMAL")
    res = sim.execute()

    assert res.deal_reached is True
    assert res.rounds_taken == 2
    assert res.agreed_allocation == award_r2.allocations
    assert res.approval_type == "unanimous_3_0"
    # Verify confidential claim inflation logged
    assert res.first_disclosed_claims["Chang-Liu Cloud Services"] == 200000
    assert res.first_disclosed_claims["G-Corp"] == 500000
