"""Condition 1: Multilateral Bargaining with Rotating Proposer (MBRP)."""

from typing import Dict, List, Optional
from src.conditions.base import BaseCondition
from src.agents import NegotiationAgent
from src.schemas import RunResult, Proposal
from src.validators import validate_split, REQUIRED_COMPANIES


class MBRPNegotiation(BaseCondition):
    """
    Multilateral Bargaining with Rotating Proposer.
    One designated proposer tables a binding split; the two responders evaluate simultaneously.
    3/3 unanimous acceptance required for agreement.
    """

    def __init__(
        self,
        run_id: str,
        run_index: int,
        agents: Dict[str, NegotiationAgent],
        model_name: str,
        thinking_level: str,
        max_rounds: int = 8,
    ):
        super().__init__(
            run_id=run_id,
            condition_id="mbrp",
            model_name=model_name,
            thinking_level=thinking_level,
            max_rounds=max_rounds,
        )
        self.run_index = run_index
        self.agents = agents
        self.company_order = list(REQUIRED_COMPANIES)
        # Balance initial proposer based on run_index: 0 -> G-Corp, 1 -> Yang, 2 -> Chang-Liu
        self.start_offset = run_index % len(self.company_order)

    def execute(self) -> RunResult:
        history_summary: List[str] = []

        for round_num in range(1, self.max_rounds + 1):
            # Determine proposer for this round
            proposer_idx = (self.start_offset + round_num - 1) % len(self.company_order)
            proposer_name = self.company_order[proposer_idx]
            responders = [c for c in self.company_order if c != proposer_name]

            # Stage 1: Proposer tables formal split
            proposer_agent = self.agents[proposer_name]
            proposer_prompt = (
                f"--- ROUND {round_num} of {self.max_rounds} ---\n"
                f"You are the DESIGNATED PROPOSER for this round.\n"
                "Please table a formal profit split allocating exactly $1,000,000 across G-Corp, Yang Industries, and Chang-Liu Cloud Services.\n"
                f"Previous round history:\n" + ("\n".join(history_summary) if history_summary else "No previous rounds.") + "\n\n"
                "In your response, provide your strategic reasoning, your public message explaining the proposal, "
                "your proposed allocation in 'counter_proposal' (which serves as the tabled split), and vote 'ACCEPT'."
            )
            proposer_resp, meta = proposer_agent.generate_response(proposer_prompt)
            self.accumulate_tokens(meta)
            self.record_claim(proposer_name, proposer_resp.claimed_walkaway)

            # Extract tabled split
            tabled_alloc = proposer_resp.counter_proposal.allocations if proposer_resp.counter_proposal else {}
            is_valid, err = validate_split(tabled_alloc)

            self.log_event(
                round_num=round_num,
                stage="table_motion",
                agent_id=proposer_name,
                payload={
                    "allocations": tabled_alloc,
                    "valid": is_valid,
                    "error": err,
                    "public_message": proposer_resp.public_message,
                    "claimed_walkaway": proposer_resp.claimed_walkaway,
                },
            )

            if not is_valid:
                # If proposer offered an invalid split, round fails immediately
                fail_msg = f"Round {round_num}: {proposer_name} tabled an invalid split ({err}). Round failed."
                history_summary.append(fail_msg)
                continue

            # Stage 2: Responders evaluate simultaneously
            responder_votes: Dict[str, str] = {}
            for resp_name in responders:
                resp_agent = self.agents[resp_name]
                resp_prompt = (
                    f"--- ROUND {round_num} of {self.max_rounds} ---\n"
                    f"{proposer_name} has tabled the following formal profit split of $1,000,000:\n"
                    f"{tabled_alloc}\n"
                    f"Message from {proposer_name}: \"{proposer_resp.public_message}\"\n\n"
                    f"Previous round history:\n" + ("\n".join(history_summary) if history_summary else "No previous rounds.") + "\n\n"
                    "Please evaluate this offer independently.\n"
                    "Vote 'ACCEPT' to finalize this agreement (requires all 3 companies to accept), or 'REJECT' to decline.\n"
                    "You may provide a public message, an optional suggested counter-proposal for future rounds, "
                    "and an optional disclosed outside option."
                )
                r_resp, r_meta = resp_agent.generate_response(resp_prompt)
                self.accumulate_tokens(r_meta)
                self.record_claim(resp_name, r_resp.claimed_walkaway)

                v = (r_resp.vote or "REJECT").upper()
                responder_votes[resp_name] = v

                self.log_event(
                    round_num=round_num,
                    stage="responder_evaluation",
                    agent_id=resp_name,
                    payload={
                        "vote": v,
                        "public_message": r_resp.public_message,
                        "claimed_walkaway": r_resp.claimed_walkaway,
                        "suggested_counterproposal": r_resp.counter_proposal.allocations if r_resp.counter_proposal else None,
                    },
                )

            # Decision Rule: 3/3 accept (proposer accepted, both responders must vote ACCEPT)
            if all(v == "ACCEPT" for v in responder_votes.values()):
                deal_msg = f"Round {round_num}: Agreement reached on {proposer_name}'s proposal: {tabled_alloc}."
                history_summary.append(deal_msg)
                return self.compile_result(
                    deal_reached=True,
                    rounds_taken=round_num,
                    agreed_allocation=tabled_alloc,
                    winning_voters=list(REQUIRED_COMPANIES),
                    approval_type="unanimous_3_0",
                )

            # If rejected, record summary and continue to next round
            rejectors = [c for c, v in responder_votes.items() if v != "ACCEPT"]
            round_summary = f"Round {round_num}: {proposer_name}'s offer {tabled_alloc} was REJECTED by {', '.join(rejectors)}."
            history_summary.append(round_summary)

        # Reached deadline without deal
        return self.compile_result(
            deal_reached=False,
            rounds_taken=self.max_rounds,
            agreed_allocation=None,
        )
