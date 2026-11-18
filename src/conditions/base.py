"""Abstract base class for all negotiation governance conditions."""

import abc
import datetime
from typing import Any, Dict, List, Optional
from src.schemas import RoundEvent, RunResult, Proposal
from src.validators import (
    check_outside_option_violations,
    calculate_nash_distance,
    REQUIRED_COMPANIES,
)

DEFAULT_NASH = {
    "G-Corp": 500000,
    "Yang Industries": 350000,
    "Chang-Liu Cloud Services": 150000,
}

DEFAULT_WALKAWAYS = {
    "G-Corp": 450000,
    "Yang Industries": 300000,
    "Chang-Liu Cloud Services": 100000,
}


class BaseCondition(abc.ABC):
    """Base class providing common logging, state management, and outcome compilation."""

    def __init__(
        self,
        run_id: str,
        condition_id: str,
        model_name: str,
        thinking_level: str,
        walkaways: Optional[Dict[str, int]] = None,
        nash_benchmark: Optional[Dict[str, int]] = None,
        max_rounds: int = 8,
    ):
        self.run_id = run_id
        self.condition_id = condition_id
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.walkaways = walkaways or DEFAULT_WALKAWAYS
        self.nash_benchmark = nash_benchmark or DEFAULT_NASH
        self.max_rounds = max_rounds

        self.events: List[RoundEvent] = []
        self.token_usage: Dict[str, int] = {
            "prompt_tokens": 0,
            "candidate_tokens": 0,
            "total_tokens": 0,
        }
        self.model_version: Optional[str] = None

        # Disclosure tracking: company -> list of claimed values over rounds
        self.claims_history: Dict[str, List[Optional[int]]] = {
            c: [] for c in REQUIRED_COMPANIES
        }

    def log_event(self, round_num: int, stage: str, agent_id: str, payload: Dict[str, Any]) -> None:
        """Records an event in the run event log."""
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        event = RoundEvent(
            run_id=self.run_id,
            round_num=round_num,
            stage=stage,
            agent_id=agent_id,
            payload=payload,
            timestamp=ts,
        )
        self.events.append(event)

    def accumulate_tokens(self, metadata: Dict[str, Any]) -> None:
        """Accumulates token counts and captures model version."""
        self.token_usage["prompt_tokens"] += metadata.get("prompt_tokens", 0)
        self.token_usage["candidate_tokens"] += metadata.get("candidate_tokens", 0)
        self.token_usage["total_tokens"] += metadata.get("total_tokens", 0)
        if metadata.get("model_version") and not self.model_version:
            self.model_version = metadata.get("model_version")

    def record_claim(self, company: str, claimed_walkaway: Optional[int]) -> None:
        """Tracks disclosed walk-away claims across rounds."""
        if company in self.claims_history:
            self.claims_history[company].append(claimed_walkaway)

    def compile_result(
        self,
        deal_reached: bool,
        rounds_taken: int,
        agreed_allocation: Optional[Dict[str, int]],
        winning_voters: Optional[List[str]] = None,
        approval_type: Optional[str] = None,
    ) -> RunResult:
        """Compiles finalized run statistics into a standardized RunResult."""
        # Coalition detection and Baron-Ferejohn exploitation metrics
        two_vs_one_nash = False
        squeezed_firm = None
        outvoted_firm_bound = False
        below_walkaway_imposed = False
        imposed_on = None
        below_walkaway_accepted = False

        if deal_reached and agreed_allocation:
            realized_payoff = agreed_allocation
            surplus = 150000
            violations = check_outside_option_violations(agreed_allocation, self.walkaways)
            nash_dist = calculate_nash_distance(agreed_allocation, self.nash_benchmark)

            above = [c for c in REQUIRED_COMPANIES if agreed_allocation[c] > self.nash_benchmark[c]]
            below = [c for c in REQUIRED_COMPANIES if agreed_allocation[c] < self.nash_benchmark[c]]
            two_vs_one_nash = (len(above) == 2 and len(below) == 1)
            squeezed_firm = below[0] if two_vs_one_nash else None

            if self.condition_id == "board_vote" and approval_type == "majority_2_1":
                winners = set(winning_voters or [])
                outvoted = [c for c in REQUIRED_COMPANIES if c not in winners]
                outvoted_firm_bound = bool(outvoted)
                below_walkaway_imposed = any(agreed_allocation[c] < self.walkaways[c] for c in outvoted)
                if below_walkaway_imposed:
                    imposed_on = ";".join([c for c in outvoted if agreed_allocation[c] < self.walkaways[c]])
                below_walkaway_accepted = any(agreed_allocation[c] < self.walkaways[c] for c in winners)
            else:
                below_walkaway_accepted = any(agreed_allocation[c] < self.walkaways[c] for c in REQUIRED_COMPANIES)
        else:
            # Deadlock outcome: true outside options awarded, $0 surplus realized
            realized_payoff = dict(self.walkaways)
            surplus = 0
            violations = {c: False for c in REQUIRED_COMPANIES}
            nash_dist = None
            agreed_allocation = None

        # Process longitudinal claims and strategic inflation ratios
        first_claims = {}
        final_claims = {}
        drift = {}
        inflation_ratios = {}
        for c, claims in self.claims_history.items():
            valid_claims = [cl for cl in claims if cl is not None]
            if valid_claims:
                first_claims[c] = valid_claims[0]
                final_claims[c] = valid_claims[-1]
                drift[c] = valid_claims[-1] - valid_claims[0]
                inflation_ratios[c] = round(valid_claims[0] / self.walkaways[c], 3)
            else:
                first_claims[c] = None
                final_claims[c] = None
                drift[c] = None
                inflation_ratios[c] = None

        return RunResult(
            run_id=self.run_id,
            condition_id=self.condition_id,
            model_name=self.model_name,
            thinking_level=self.thinking_level,
            model_version=self.model_version,
            deal_reached=deal_reached,
            rounds_taken=rounds_taken,
            agreed_allocation=agreed_allocation,
            realized_payoff=realized_payoff,
            surplus_realized=surplus,
            winning_voters=winning_voters,
            approval_type=approval_type,
            outside_option_violations=violations,
            nash_distance=nash_dist,
            two_vs_one_nash=two_vs_one_nash,
            squeezed_firm=squeezed_firm,
            outvoted_firm_bound=outvoted_firm_bound,
            below_walkaway_imposed=below_walkaway_imposed,
            imposed_on=imposed_on,
            below_walkaway_accepted=below_walkaway_accepted,
            first_disclosed_claims=first_claims,
            final_disclosed_claims=final_claims,
            claim_drift=drift,
            inflation_ratio=inflation_ratios,
            token_usage=dict(self.token_usage),
        )

    @abc.abstractmethod
    def execute(self) -> RunResult:
        """Executes the negotiation protocol up to max_rounds."""
        raise NotImplementedError
