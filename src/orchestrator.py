"""Experiment orchestrator: initializes agents, executes negotiation runs, and logs outcomes.
Supports both homogeneous runs and heterogeneous mixed-model allocations.
"""

from typing import Any, Dict, Optional
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
    model_name: str = "gemini-3.5-flash-lite",
    thinking_level: str = "MINIMAL",
    provider: str = "gemini",
    temperature: Optional[float] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    run_index: int = 0,
    max_rounds: int = 8,
    agent_configs: Optional[Dict[str, Dict[str, Any]]] = None,
    arbitrator_config: Optional[Dict[str, Any]] = None,
) -> RunResult:
    """
    Executes a single negotiation simulation end-to-end.
    
    Args:
        run_id: Unique identifier for this run.
        condition_id: One of 'mbrp', 'free', 'board_vote', 'arbitrator'.
        model_name: Default model identifier (e.g. 'gemini-3.5-flash-lite', 'gpt-4o', 'claude-haiku-5-5').
        thinking_level: 'MINIMAL', 'LOW', 'MEDIUM', 'HIGH' (for reasoning models).
        provider: 'gemini', 'openai', or 'anthropic'.
        temperature: Sampling temperature (for models that support it).
        base_url: Optional base URL (e.g. for local Ollama).
        api_key: Optional API key override.
        run_index: 0-indexed repetition counter (used for proposer balancing).
        max_rounds: Maximum negotiation rounds (default 8).
        agent_configs: Optional dictionary assigning specific models/providers per company:
            {
                "G-Corp": {"provider": "anthropic", "model_name": "claude-haiku-5-5"},
                "Yang Industries": {"provider": "openai", "model_name": "gpt-4o"},
                "Chang-Liu Cloud Services": {"provider": "gemini", "model_name": "gemini-3.8-flash"}
            }
        arbitrator_config: Optional specific provider/model config for the neutral arbitrator.

    Returns:
        Finalized RunResult instance.
    """
    # Initialize company agents (either from agent_configs or default model_name)
    agents: Dict[str, NegotiationAgent] = {}
    for cfg in COMPANIES_CONFIG:
        c_name = cfg["name"]
        if agent_configs and c_name in agent_configs:
            c_cfg = agent_configs[c_name]
            c_provider = c_cfg.get("provider", provider)
            c_model = c_cfg.get("model_name", model_name)
            c_think = c_cfg.get("thinking_level", thinking_level)
            c_temp = c_cfg.get("temperature", temperature)
            c_base = c_cfg.get("base_url", base_url)
            c_key = c_cfg.get("api_key", api_key)
        else:
            c_provider = provider
            c_model = model_name
            c_think = thinking_level
            c_temp = temperature
            c_base = base_url
            c_key = api_key

        agents[c_name] = NegotiationAgent(
            company_name=c_name,
            role=cfg["role"],
            walkaway=cfg["walkaway"],
            model_name=c_model,
            thinking_level=c_think,
            provider=c_provider,
            temperature=c_temp,
            base_url=c_base,
            api_key=c_key,
        )

    # Effective tag for model reporting in metadata
    if agent_configs:
        effective_model_tag = "mixed_" + "-".join(f"{k[:3]}:{v.get('model_name','')[:7]}" for k, v in sorted(agent_configs.items()))
    else:
        effective_model_tag = model_name

    # Initialize and execute condition
    if condition_id == "mbrp":
        condition = MBRPNegotiation(
            run_id=run_id,
            run_index=run_index,
            agents=agents,
            model_name=effective_model_tag,
            thinking_level=thinking_level,
            max_rounds=max_rounds,
        )
    elif condition_id in ("free", "free_negotiation"):
        condition = FreeNegotiation(
            run_id=run_id,
            run_index=run_index,
            agents=agents,
            model_name=effective_model_tag,
            thinking_level=thinking_level,
            max_rounds=max_rounds,
        )
    elif condition_id == "board_vote":
        condition = BoardVoteNegotiation(
            run_id=run_id,
            agents=agents,
            model_name=effective_model_tag,
            thinking_level=thinking_level,
            max_rounds=max_rounds,
        )
    elif condition_id == "arbitrator":
        arb_cfg = arbitrator_config or {}
        arbitrator = ArbitratorAgent(
            model_name=arb_cfg.get("model_name", model_name),
            thinking_level=arb_cfg.get("thinking_level", thinking_level),
            provider=arb_cfg.get("provider", provider),
            temperature=arb_cfg.get("temperature", temperature),
            base_url=arb_cfg.get("base_url", base_url),
            api_key=arb_cfg.get("api_key", api_key),
        )
        condition = ArbitratorNegotiation(
            run_id=run_id,
            agents=agents,
            arbitrator=arbitrator,
            model_name=effective_model_tag,
            thinking_level=thinking_level,
            max_rounds=max_rounds,
        )
    else:
        raise ValueError(f"Unknown condition_id: '{condition_id}'. Must be 'mbrp', 'free', 'board_vote', or 'arbitrator'.")

    # Run the simulation
    result = condition.execute()

    # Save transcript and summary
    save_transcript(condition.events, run_id, condition_id, effective_model_tag)
    append_summary_csv(result)

    return result
