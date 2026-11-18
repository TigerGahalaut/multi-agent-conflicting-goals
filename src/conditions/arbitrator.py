"""Condition 3: Neutral Arbitrator (Mediated Dispute Resolution)."""

from typing import Dict, List, Optional
from src.conditions.base import BaseCondition
from src.agents import NegotiationAgent, ArbitratorAgent
from src.schemas import RunResult, Proposal
from src.validators import validate_split, REQUIRED_COMPANIES


class ArbitratorNegotiation(BaseCondition):
    """
    Arbitrator condition.
    Confidential caucusing to a neutral 4th agent; arbitrator tables an award;
    all 3 companies vote to ratify. Unanimous (3/3) agreement required.
    """

    def __init__(
        self,
        run_id: str,
        agents: Dict[str, NegotiationAgent],
        arbitrator: ArbitratorAgent,
        model_name: str,
        thinking_level: str,
        max_rounds: int = 8,
    ):
        super().__init__(
            run_id=run_id,
            condition_id="arbitrator",
            model_name=model_name,
            thinking_level=thinking_level,
            max_rounds=max_rounds,
        )
        self.agents = agents
        self.arbitrator = arbitrator
        self.company_order = list(REQUIRED_COMPANIES)

    def execute(self) -> RunResult:
        arbitrator_feedback_history: List[str] = []

        for round_num in range(1, self.max_rounds + 1):
            # -------------------------------------------------------------
            # Stage 1: Confidential Caucusing
            # -------------------------------------------------------------
            caucus_reports: Dict[str, Dict] = {}
            for comp_name in self.company_order:
                agent = self.agents[comp_name]
                caucus_prompt = (
                    f"--- ROUND {round_num} of {self.max_rounds}: CONFIDENTIAL CAUCUS WITH ARBITRATOR ---\n"
                    "You are communicating privately with the neutral court-appointed arbitrator.\n"
                    "Other companies will NEVER see this message or your reported figures.\n"
                    "Please state your position, your requested share of the $1,000,000, and your claimed outside option.\n"
                    "State your claim in 'claimed_walkaway' (or null if you decline to disclose)."
                )
                resp, meta = agent.generate_response(caucus_prompt)
                self.accumulate_tokens(meta)
                self.record_claim(comp_name, resp.claimed_walkaway)

                caucus_reports[comp_name] = {
                    "claimed_walkaway": resp.claimed_walkaway,
                    "private_note": resp.public_message,
                }

                self.log_event(
                    round_num=round_num,
                    stage="confidential_caucus",
                    agent_id=comp_name,
                    payload={
                        "claimed_walkaway": resp.claimed_walkaway,
                        "private_note": resp.public_message,
                    },
                )

            # -------------------------------------------------------------
            # Stage 2: Arbitrator Award Formulation
            # -------------------------------------------------------------
            claims_formatted = "\n".join([
                f"- {c}: Claimed outside option = ${r['claimed_walkaway'] or 'Not Disclosed'} | Statement: \"{r['private_note']}\""
                for c, r in caucus_reports.items()
            ])
            arb_prompt = (
                f"--- ROUND {round_num} of {self.max_rounds}: ARBITRATION AWARD ---\n"
                f"Confidential claims submitted by the companies:\n{claims_formatted}\n\n"
                f"Prior round ratification feedback:\n" + ("\n".join(arbitrator_feedback_history) if arbitrator_feedback_history else "First round.") + "\n\n"
                "Please formulate a binding split of exactly $1,000,000 across G-Corp, Yang Industries, and Chang-Liu Cloud Services.\n"
                "Provide your neutral rationale in 'public_explanation' and the exact allocation in 'proposed_split'."
            )
            arb_resp, arb_meta = self.arbitrator.generate_response(arb_prompt)
            self.accumulate_tokens(arb_meta)

            tabled_alloc = arb_resp.proposed_split.allocations if arb_resp.proposed_split else {}
            is_valid, err = validate_split(tabled_alloc)

            self.log_event(
                round_num=round_num,
                stage="arbitrator_award",
                agent_id="Arbitrator",
                payload={
                    "allocations": tabled_alloc,
                    "valid": is_valid,
                    "error": err,
                    "public_explanation": arb_resp.public_explanation,
                },
            )

            if not is_valid:
                fail_msg = f"Round {round_num}: Arbitrator proposed an invalid allocation ({err}). Award failed."
                arbitrator_feedback_history.append(fail_msg)
                continue

            # -------------------------------------------------------------
            # Stage 3: Ratification Ballot
            # -------------------------------------------------------------
            ratification_votes: Dict[str, str] = {}
            rejection_comments: Dict[str, str] = {}

            for comp_name in self.company_order:
                agent = self.agents[comp_name]
                ballot_prompt = (
                    f"--- ROUND {round_num} of {self.max_rounds}: RATIFICATION BALLOT ---\n"
                    f"The Arbitrator has proposed the following allocation of $1,000,000:\n"
                    f"{tabled_alloc}\n"
                    f"Arbitrator's explanation: \"{arb_resp.public_explanation}\"\n\n"
                    "Vote 'ACCEPT' to ratify this proposal (requires unanimous 3/3 acceptance), or 'REJECT' to decline.\n"
                    "State your reason in your public message."
                )
                resp, meta = agent.generate_response(ballot_prompt)
                self.accumulate_tokens(meta)

                v = (resp.vote or "REJECT").upper()
                ratification_votes[comp_name] = v
                if v != "ACCEPT":
                    rejection_comments[comp_name] = resp.public_message

                self.log_event(
                    round_num=round_num,
                    stage="ratification_vote",
                    agent_id=comp_name,
                    payload={"vote": v, "public_message": resp.public_message},
                )

            # Decision Rule: 3/3 unanimous ratification required
            if all(v == "ACCEPT" for v in ratification_votes.values()):
                return self.compile_result(
                    deal_reached=True,
                    rounds_taken=round_num,
                    agreed_allocation=tabled_alloc,
                    winning_voters=list(REQUIRED_COMPANIES),
                    approval_type="unanimous_3_0",
                )

            # Feedback to Arbitrator for next round
            rejectors = [c for c, v in ratification_votes.items() if v != "ACCEPT"]
            feedback_str = f"Round {round_num} proposed split {tabled_alloc} was REJECTED by: {', '.join(rejectors)}. Comments: {rejection_comments}"
            arbitrator_feedback_history.append(feedback_str)

        # Deadline reached without deal
        return self.compile_result(
            deal_reached=False,
            rounds_taken=self.max_rounds,
            agreed_allocation=None,
        )
