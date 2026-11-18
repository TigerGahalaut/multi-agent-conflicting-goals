"""Pydantic schemas for data structures, model responses, and event logging."""

from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class Proposal(BaseModel):
    """A proposed split of the $1,000,000 profit among the three companies."""
    g_corp: int = Field(
        default=0,
        description="Allocation in dollars for G-Corp (chip designer)"
    )
    yang_industries: int = Field(
        default=0,
        description="Allocation in dollars for Yang Industries (manufacturer)"
    )
    chang_liu: int = Field(
        default=0,
        description="Allocation in dollars for Chang-Liu Cloud Services (cloud provider)"
    )

    def __init__(self, allocations: Optional[Dict[str, int]] = None, **data):
        if allocations is not None:
            data["g_corp"] = allocations.get("G-Corp", 0)
            data["yang_industries"] = allocations.get("Yang Industries", 0)
            data["chang_liu"] = allocations.get("Chang-Liu Cloud Services", 0)
        super().__init__(**data)

    @property
    def allocations(self) -> Dict[str, int]:
        return {
            "G-Corp": self.g_corp,
            "Yang Industries": self.yang_industries,
            "Chang-Liu Cloud Services": self.chang_liu,
        }


class CompanyAgentResponse(BaseModel):
    """Structured response from a company negotiator agent."""
    reasoning: str = Field(
        ...,
        description="Private internal strategic thinking (not visible to other negotiators)"
    )
    public_message: str = Field(
        ...,
        description="Message visible to other negotiators (or confidential note to arbitrator)"
    )
    claimed_walkaway: Optional[int] = Field(
        default=None,
        description="Optional outside option / walk-away value disclosed (leave null/None if keeping private)"
    )
    vote: Optional[Literal["ACCEPT", "REJECT", "YES", "NO"]] = Field(
        default=None,
        description="Vote on active proposal/motion: 'ACCEPT'/'REJECT' in MBRP & Arbitrator, 'YES'/'NO' in Board Vote"
    )
    ballot: Optional[Dict[str, Literal["YES", "NO"]]] = Field(
        default=None,
        description="Optional map of company name -> 'YES'/'NO' vote for each tabled motion in Board Vote"
    )
    counter_proposal: Optional[Proposal] = Field(
        default=None,
        description="Optional non-binding suggestion for future rounds (in MBRP) or informal proposal"
    )


class ArbitratorResponse(BaseModel):
    """Structured response from the neutral 4th arbitrator agent."""
    reasoning: str = Field(
        ...,
        description="Impartial analysis of claims and fair surplus distribution"
    )
    public_explanation: str = Field(
        ...,
        description="Neutral explanation presented to the three companies"
    )
    proposed_split: Proposal = Field(
        ...,
        description="Binding split proposal to be ratified by the companies"
    )


class BallotVote(BaseModel):
    """A vote cast by an agent on a specific tabled proposal in Board Vote."""
    voter: str
    proposal_owner: str
    vote: Literal["YES", "NO"]


class RoundEvent(BaseModel):
    """Structured event record for event-stream logging."""
    run_id: str
    round_num: int
    stage: str
    agent_id: str
    payload: Dict
    timestamp: str


class RunResult(BaseModel):
    """Complete summary of a single negotiation run."""
    run_id: str
    condition_id: str
    model_name: str
    thinking_level: str
    model_version: Optional[str] = None
    deal_reached: bool
    rounds_taken: int
    agreed_allocation: Optional[Dict[str, int]] = None
    realized_payoff: Dict[str, int]
    surplus_realized: int
    winning_voters: Optional[List[str]] = None
    approval_type: Optional[Literal["unanimous_3_0", "majority_2_1"]] = None
    outside_option_violations: Dict[str, bool]
    nash_distance: Optional[float] = None
    first_disclosed_claims: Dict[str, Optional[int]]
    final_disclosed_claims: Dict[str, Optional[int]]
    claim_drift: Dict[str, Optional[int]]
    token_usage: Dict[str, int]
