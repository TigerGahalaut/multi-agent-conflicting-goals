"""Experiment orchestrator: initializes agents, executes negotiation runs, and logs outcomes."""

from typing import Dict, Optional
from src.agents import NegotiationAgent, ArbitratorAgent
from src.schemas import RunResult
from src.conditions.mbrp import MBRPNegotiation
from src.conditions.free_negotiation import FreeNegotiation
from src.conditions.board_vote import BoardVoteNegotiation
from src.conditions.arbitrator import ArbitratorNegotiation
from src.storage import save_transcript, append_summary_csv

COMPANIES_CONFIG = [
    {"name": "G-Corp", "role": "Chip designer", "walkaway": 450000},
    {"name": "Yang Industries", "role": "Manufacturer", "walkaway": 300000},
    {"name": "Chang-Liu Cloud Services", "role": "Cloud provider", "walkaway": 100000},
]


def run_single_negotiation(
    run_id: str,
    condition_id: str,
    model_name: str,
    thinking_level: str,
    run_index: int = 0,
    max_rounds: int = 8,
) -> RunResult:
    """
    Executes a single negotiation simulation end-to-end.
    
    Args:
        run_id: Unique identifier for this run.
        condition_id: One of 'mbrp', 'board_vote', 'arbitrator'.
        model_name: e.g. 'gemini-3.5-flash-lite' or 'gemini-3.8-flash'.
        thinking_level: 'MINIMAL' or 'LOW'.
        run_index: 0-indexed repetition counter (used for proposer balancing).
        max_rounds: Maximum negotiation rounds (default 8).

    Returns:
        Finalized RunResult instance.
    """
    # Initialize company agents
    agents: Dict[str, NegotiationAgent] = {}
    for cfg in COMPANIES_CONFIG:
        agents[cfg["name"]] = NegotiationAgent(
            company_name=cfg["name"],
            role=cfg["role"],
            walkaway=cfg["walkaway"],
            model_name=model_name,
            thinking_level=thinking_level,
        )

    # Initialize and execute condition
    if condition_id == "mbrp":
        condition = MBRPNegotiation(
            run_id=run_id,
            run_index=run_index,
            agents=agents,
            model_name=model_name,
            thinking_level=thinking_level,
            max_rounds=max_rounds,
        )
    elif condition_id in ("free", "free_negotiation"):
        condition = FreeNegotiation(
            run_id=run_id,
            run_index=run_index,
            agents=agents,
            model_name=model_name,
            thinking_level=thinking_level,
            max_rounds=max_rounds,
        )
    elif condition_id == "board_vote":
        condition = BoardVoteNegotiation(
            run_id=run_id,
            agents=agents,
            model_name=model_name,
            thinking_level=thinking_level,
            max_rounds=max_rounds,
        )
    elif condition_id == "arbitrator":
        arbitrator = ArbitratorAgent(
            model_name=model_name,
            thinking_level=thinking_level,
        )
        condition = ArbitratorNegotiation(
            run_id=run_id,
            agents=agents,
            arbitrator=arbitrator,
            model_name=model_name,
            thinking_level=thinking_level,
            max_rounds=max_rounds,
        )
    else:
        raise ValueError(f"Unknown condition_id: '{condition_id}'. Must be 'mbrp', 'free', 'board_vote', or 'arbitrator'.")

    # Run the simulation
    result = condition.execute()

    # Save transcript and summary
    save_transcript(condition.events, run_id, condition_id, model_name)
    append_summary_csv(result)

    return result
