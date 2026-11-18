"""Condition 2: Board Vote (Legislative Majority Bargaining)."""

import json
from typing import Dict, List, Optional
from src.conditions.base import BaseCondition
from src.agents import NegotiationAgent
from src.schemas import RunResult, Proposal
from src.validators import (
    validate_split,
    evaluate_board_ballot,
    REQUIRED_COMPANIES,
)


class BoardVoteNegotiation(BaseCondition):
    """
    Board Vote condition.
    3-Stage sequence per round:
      1. Simultaneous Public Signaling (one-shot statements / coalition pitches)
      2. Formal Motion Submission (all 3 table a split)
      3. Simultaneous Secret Ballot (all 3 vote YES/NO on all valid tabled motions)
    >= 2 YES votes binds all parties. Seeded tie-breaker for equal votes.
    """

    def __init__(
        self,
        run_id: str,
        agents: Dict[str, NegotiationAgent],
        model_name: str,
        thinking_level: str,
        max_rounds: int = 8,
    ):
        super().__init__(
            run_id=run_id,
            condition_id="board_vote",
            model_name=model_name,
            thinking_level=thinking_level,
            max_rounds=max_rounds,
        )
        self.agents = agents
        self.company_order = list(REQUIRED_COMPANIES)

    def execute(self) -> RunResult:
        history_summary: List[str] = []

        for round_num in range(1, self.max_rounds + 1):
            # -------------------------------------------------------------
            # Stage 1: Simultaneous Public Signaling
            # -------------------------------------------------------------
            signaling_statements: Dict[str, str] = {}
            for comp_name in self.company_order:
                agent = self.agents[comp_name]
                sig_prompt = (
                    f"--- ROUND {round_num} of {self.max_rounds}: STAGE 1 (PUBLIC SIGNALING) ---\n"
                    "This is the open deliberation stage before formal motions are tabled.\n"
                    f"Previous round history:\n" + ("\n".join(history_summary) if history_summary else "No previous rounds.") + "\n\n"
                    "Provide a public message to the other two companies (e.g., discuss preferred splits, "
                    "signal coalition intentions, or debate outside options). "
                    "You may also optionally disclose your claimed outside option."
                )
                resp, meta = agent.generate_response(sig_prompt)
                self.accumulate_tokens(meta)
                self.record_claim(comp_name, resp.claimed_walkaway)
                signaling_statements[comp_name] = resp.public_message

                self.log_event(
                    round_num=round_num,
                    stage="public_signaling",
                    agent_id=comp_name,
                    payload={
                        "public_message": resp.public_message,
                        "claimed_walkaway": resp.claimed_walkaway,
                    },
                )

            # -------------------------------------------------------------
            # Stage 2: Formal Motion Submission
            # -------------------------------------------------------------
            tabled_motions: List[Dict] = []
            for comp_name in self.company_order:
                agent = self.agents[comp_name]
                signals_formatted = "\n".join([f"- {c}: \"{msg}\"" for c, msg in signaling_statements.items()])
                motion_prompt = (
                    f"--- ROUND {round_num} of {self.max_rounds}: STAGE 2 (FORMAL MOTION) ---\n"
                    "Public statements from Stage 1:\n" + signals_formatted + "\n\n"
                    "Please submit your formal motion for a profit split of $1,000,000 across G-Corp, Yang Industries, and Chang-Liu Cloud Services.\n"
                    "Put the exact allocation in 'counter_proposal' and explain the motion in your 'public_message'."
                )
                resp, meta = agent.generate_response(motion_prompt)
                self.accumulate_tokens(meta)

                alloc = resp.counter_proposal.allocations if resp.counter_proposal else {}
                is_valid, err = validate_split(alloc)
                if is_valid:
                    motion_obj = {"proposer": comp_name, "allocations": alloc}
                    tabled_motions.append(motion_obj)

                self.log_event(
                    round_num=round_num,
                    stage="table_motion",
                    agent_id=comp_name,
                    payload={
                        "allocations": alloc,
                        "valid": is_valid,
                        "error": err,
                        "public_message": resp.public_message,
                    },
                )

            if not tabled_motions:
                fail_msg = f"Round {round_num}: No valid motions were tabled. Round failed."
                history_summary.append(fail_msg)
                continue

            # -------------------------------------------------------------
            # Stage 3: Simultaneous Secret Ballot
            # -------------------------------------------------------------
            ballots: List[Dict] = []
            motions_summary = "\n".join([
                f"Motion by {m['proposer']}: {m['allocations']}" for m in tabled_motions
            ])

            for comp_name in self.company_order:
                agent = self.agents[comp_name]
                ballot_prompt = (
                    f"--- ROUND {round_num} of {self.max_rounds}: STAGE 3 (SECRET BALLOT) ---\n"
                    "The following valid motions have been tabled for a vote:\n"
                    f"{motions_summary}\n\n"
                    "Rule: Any motion receiving >= 2 YES votes is legally binding on all parties.\n"
                    "If multiple motions receive equal votes, the winner is decided by an ex-ante neutral tie-breaker.\n\n"
                    "Cast your votes in the 'ballot' field as a dictionary mapping each proposer's exact name to 'YES' or 'NO':\n"
                    "Example: {\"G-Corp\": \"YES\", \"Yang Industries\": \"NO\", \"Chang-Liu Cloud Services\": \"NO\"}\n"
                    "Also summarize your voting rationale in 'public_message'."
                )
                resp, meta = agent.generate_response(ballot_prompt)
                self.accumulate_tokens(meta)

                # Collect ballot votes per motion
                agent_ballot = resp.ballot or {}
                msg_upper = (resp.public_message or "").upper()

                for motion in tabled_motions:
                    proposer = motion["proposer"]
                    if proposer in agent_ballot:
                        vote_val = agent_ballot[proposer]
                    elif any(alias in msg_upper for alias in [proposer.upper(), proposer.split()[0].upper()]):
                        # Match by full name or first word (e.g. "CHANG-LIU")
                        matched_alias = next(a for a in [proposer.upper(), proposer.split()[0].upper()] if a in msg_upper)
                        part = msg_upper.split(matched_alias)[1][:30]
                        vote_val = "YES" if "YES" in part else ("NO" if "NO" in part else ("YES" if comp_name == proposer else "NO"))
                    else:
                        vote_val = "YES" if comp_name == proposer else "NO"

                    ballots.append({
                        "voter": comp_name,
                        "target_proposer": proposer,
                        "vote": vote_val,
                    })

                self.log_event(
                    round_num=round_num,
                    stage="cast_ballot",
                    agent_id=comp_name,
                    payload={"ballot": agent_ballot, "raw_message": resp.public_message},
                )

            # Evaluate ballot
            winning_motion, winning_voters, approval_type = evaluate_board_ballot(
                tabled_motions, ballots, self.run_id, round_num
            )

            if winning_motion is not None:
                deal_msg = (
                    f"Round {round_num}: Binding agreement enacted on {winning_motion['proposer']}'s motion: "
                    f"{winning_motion['allocations']} with votes from {', '.join(winning_voters)} ({approval_type})."
                )
                history_summary.append(deal_msg)
                return self.compile_result(
                    deal_reached=True,
                    rounds_taken=round_num,
                    agreed_allocation=winning_motion["allocations"],
                    winning_voters=winning_voters,
                    approval_type=approval_type,
                )

            # If no motion achieved majority
            fail_msg = f"Round {round_num}: None of the {len(tabled_motions)} motions achieved a >= 2 majority."
            history_summary.append(fail_msg)

        # Reached deadline without deal
        return self.compile_result(
            deal_reached=False,
            rounds_taken=self.max_rounds,
            agreed_allocation=None,
        )
