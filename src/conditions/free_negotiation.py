"""Condition 1b: Free Negotiation (Behavioral Conversational Simulation)."""

import hashlib
import random
from typing import Dict, List, Optional, Set
from src.conditions.base import BaseCondition
from src.agents import NegotiationAgent
from src.schemas import RunResult
from src.validators import validate_split, REQUIRED_COMPANIES


class FreeNegotiation(BaseCondition):
    """
    Free Negotiation (Organic Behavioral Simulation).
    In each round, companies take sequential turns in a randomized/balanced order.
    On its turn, an agent may:
      1. 'propose': Tables a new profit split of $1,000,000 (clears prior acceptances; proposer accepts).
      2. 'accept': Accepts the currently active proposal.
      3. 'pass': Speaks or critiques without altering the proposal/acceptance state.
    A deal is finalized immediately as soon as all 3 companies have accepted the active proposal.
    """

    def __init__(
        self,
        run_id: str,
        run_index: int,
        agents: Dict[str, NegotiationAgent],
        model_name: str,
        thinking_level: str,
        max_rounds: int = 8,
        walkaways: Optional[Dict[str, int]] = None,
        nash_benchmark: Optional[Dict[str, int]] = None,
    ):
        super().__init__(
            run_id=run_id,
            condition_id="free",
            model_name=model_name,
            thinking_level=thinking_level,
            walkaways=walkaways,
            nash_benchmark=nash_benchmark,
            max_rounds=max_rounds,
        )
        self.run_index = run_index
        self.agents = agents
        self.company_order = list(REQUIRED_COMPANIES)
        # Reproducible seed for order shuffling per run
        seed_int = int(hashlib.sha256(f"{run_id}_free_seed".encode()).hexdigest()[:8], 16)
        self.rng = random.Random(seed_int)

    def execute(self) -> RunResult:
        transcript_history: List[str] = []
        current_proposal: Optional[Dict[str, int]] = None
        current_proposer: Optional[str] = None
        accepted_firms: Set[str] = set()

        for round_num in range(1, self.max_rounds + 1):
            print(f"  -> Round {round_num}/{self.max_rounds} (Free Deliberation)...", flush=True)
            # Fixed random turn order per round for ecological realism
            turn_order = list(self.company_order)
            self.rng.shuffle(turn_order)

            round_header = f"=== ROUND {round_num} of {self.max_rounds} ==="
            transcript_history.append(round_header)

            for comp_name in turn_order:
                agent = self.agents[comp_name]

                # Format current proposal status for the agent
                if current_proposal is not None:
                    active_status = (
                        f"Active Proposal on the table (proposed by {current_proposer}):\n"
                        f"  G-Corp: ${current_proposal.get('G-Corp', 0):,}\n"
                        f"  Yang Industries: ${current_proposal.get('Yang Industries', 0):,}\n"
                        f"  Chang-Liu Cloud Services: ${current_proposal.get('Chang-Liu Cloud Services', 0):,}\n"
                        f"Accepted by: {', '.join(sorted(accepted_firms))}\n"
                        f"Still needed: {', '.join(sorted(set(self.company_order) - accepted_firms))}"
                    )
                else:
                    active_status = "No active proposal on the table yet. Any company may propose one."

                # Construct prompt for current agent's turn
                turn_prompt = (
                    f"--- ROUND {round_num} of {self.max_rounds} | YOUR TURN: {comp_name} ---\n\n"
                    f"{active_status}\n\n"
                    f"Recent Negotiation Transcript:\n"
                    + ("\n".join(transcript_history[-15:]) if transcript_history else "No messages yet.")
                    + "\n\n"
                    "INSTRUCTIONS FOR YOUR TURN:\n"
                    "1. Set 'action' to one of:\n"
                    "   - 'propose': Table a new profit split dividing exactly $1,000,000 (set 'proposal'). "
                    "This replaces any previous proposal, resets previous acceptances, and counts you as ACCEPTING.\n"
                    "   - 'accept': Accept the currently active proposal (requires an active proposal on the table).\n"
                    "   - 'pass': Make a strategic statement, critique offers, or negotiate without changing proposal state.\n"
                    "2. In 'public_message', state what you want to communicate publicly to the other negotiators.\n"
                    "3. In 'claimed_walkaway', you may optionally disclose or restate an outside option (or null/None to keep private).\n"
                    "4. In 'reasoning', explain your private strategic calculation."
                )

                resp, meta = agent.generate_response(turn_prompt)
                self.accumulate_tokens(meta)
                self.record_claim(comp_name, resp.claimed_walkaway)

                action = (resp.action or "pass").lower().strip()
                if action not in ("propose", "accept", "pass"):
                    action = "pass"

                # Handle Propose
                if action == "propose":
                    # Check proposal field, fallback to counter_proposal if present
                    prop_obj = resp.proposal or resp.counter_proposal
                    alloc = prop_obj.allocations if prop_obj else {}
                    is_valid, err = validate_split(alloc)

                    if is_valid:
                        current_proposal = alloc
                        current_proposer = comp_name
                        accepted_firms = {comp_name}
                        event_msg = f"[Round {round_num}] {comp_name} PROPOSES {alloc}: \"{resp.public_message}\""
                        stage_name = "turn_propose"
                    else:
                        # Invalid proposal falls back to pass with notice
                        action = "pass"
                        event_msg = f"[Round {round_num}] {comp_name} attempted invalid proposal ({err}) | Passed: \"{resp.public_message}\""
                        stage_name = "turn_invalid_propose"

                    transcript_history.append(event_msg)
                    self.log_event(
                        round_num=round_num,
                        stage=stage_name,
                        agent_id=comp_name,
                        payload={
                            "action": action,
                            "proposal": current_proposal if stage_name == "turn_propose" else alloc,
                            "valid": is_valid,
                            "error": err,
                            "public_message": resp.public_message,
                            "claimed_walkaway": resp.claimed_walkaway,
                            "accepted_firms": list(accepted_firms),
                        },
                    )

                # Handle Accept
                elif action == "accept":
                    if current_proposal is not None:
                        accepted_firms.add(comp_name)
                        event_msg = f"[Round {round_num}] {comp_name} ACCEPTS proposal by {current_proposer}: \"{resp.public_message}\""
                    else:
                        # Cannot accept non-existent proposal; treated as pass
                        action = "pass"
                        event_msg = f"[Round {round_num}] {comp_name} attempted to accept but no active proposal exists: \"{resp.public_message}\""

                    transcript_history.append(event_msg)
                    self.log_event(
                        round_num=round_num,
                        stage="turn_accept",
                        agent_id=comp_name,
                        payload={
                            "action": action,
                            "target_proposer": current_proposer,
                            "accepted_proposal": current_proposal,
                            "public_message": resp.public_message,
                            "claimed_walkaway": resp.claimed_walkaway,
                            "accepted_firms": list(accepted_firms),
                        },
                    )

                # Handle Pass
                else:
                    event_msg = f"[Round {round_num}] {comp_name} passes: \"{resp.public_message}\""
                    transcript_history.append(event_msg)
                    self.log_event(
                        round_num=round_num,
                        stage="turn_pass",
                        agent_id=comp_name,
                        payload={
                            "action": "pass",
                            "public_message": resp.public_message,
                            "claimed_walkaway": resp.claimed_walkaway,
                            "active_proposal": current_proposal,
                            "accepted_firms": list(accepted_firms),
                        },
                    )

                # Check consensus termination condition
                if len(accepted_firms) == len(self.company_order) and current_proposal is not None:
                    deal_msg = f"*** DEAL REACHED in Round {round_num} on proposal by {current_proposer}: {current_proposal} ***"
                    transcript_history.append(deal_msg)
                    self.log_event(
                        round_num=round_num,
                        stage="deal_finalized",
                        agent_id="SYSTEM",
                        payload={
                            "agreed_allocation": current_proposal,
                            "proposer": current_proposer,
                            "unanimous_voters": list(self.company_order),
                        },
                    )
                    return self.compile_result(
                        deal_reached=True,
                        rounds_taken=round_num,
                        agreed_allocation=current_proposal,
                        winning_voters=list(self.company_order),
                        approval_type="unanimous_3_0",
                    )

        # 8 rounds expired without full consensus -> Deadlock
        deadlock_msg = f"*** DEADLOCK: No unanimous deal reached after {self.max_rounds} rounds. Venture cancelled. ***"
        transcript_history.append(deadlock_msg)
        return self.compile_result(
            deal_reached=False,
            rounds_taken=self.max_rounds,
            agreed_allocation=None,
        )
