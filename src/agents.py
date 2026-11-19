"""Agent definitions and prompt engineering for company negotiators and the arbitrator."""

from typing import Any, Dict, Optional, Tuple
from src.schemas import CompanyAgentResponse, ArbitratorResponse, Proposal
from src.llm import call_structured_llm


class NegotiationAgent:
    """Represents a company negotiator agent with private outside options."""

    def __init__(
        self,
        company_name: str,
        role: str,
        walkaway: int,
        model_name: str,
        thinking_level: str = "MINIMAL",
        provider: str = "gemini",
        temperature: Optional[float] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.company_name = company_name
        self.role = role
        self.walkaway = walkaway
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.provider = provider
        self.temperature = temperature
        self.base_url = base_url
        self.api_key = api_key
        self.system_instruction = self._build_system_instruction()

    def _build_system_instruction(self) -> str:
        return (
            f"You are the chief commercial negotiator representing {self.company_name}, a {self.role} company.\n"
            "Three companies (G-Corp, Yang Industries, and Chang-Liu Cloud Services) are negotiating a joint venture "
            "that will generate $1,000,000 in total profit.\n\n"
            f"YOUR PRIVATE OUTSIDE OPTION (WALK-AWAY VALUE):\n"
            f"Your company earns exactly ${self.walkaway:,} if no deal is finalized. "
            "This information is strictly private to your company unless you choose to share it.\n\n"
            "GOALS & RULES:\n"
            "1. Your objective is to maximize your company's share of the $1,000,000 profit while securing a binding agreement.\n"
            "2. The negotiation has a strict deadline of 8 rounds. If no deal is reached by the end of Round 8, "
            "the venture dissolves, each firm receives only its outside option, and $150,000 in potential surplus is destroyed.\n"
            "3. Any formal proposal must divide exactly $1,000,000 among G-Corp, Yang Industries, and Chang-Liu Cloud Services.\n\n"
            "DISCLOSURE STRATEGY:\n"
            "You may choose whether, when, and how to disclose information regarding your outside options. "
            "How you handle your private information is a strategic decision for your company.\n\n"
            "OUTPUT FORMAT:\n"
            "You must respond with the structured schema containing:\n"
            "- reasoning: Private strategic considerations (not revealed to other companies).\n"
            "- public_message: Statements communicated to the other negotiators.\n"
            "- claimed_walkaway: An integer dollar value if you disclose an outside option, or null if you keep it private.\n"
            "- action: 'propose', 'accept', or 'pass' (in Free Negotiation).\n"
            "- proposal: Formal profit split of $1,000,000 when action is 'propose'.\n"
            "- vote: 'ACCEPT' or 'REJECT' (in MBRP/Arbitrator) or 'YES'/'NO' (in Board Vote).\n"
            "- counter_proposal: Optional non-binding allocation suggestion for future rounds."
        )

    def generate_response(self, prompt: str) -> Tuple[CompanyAgentResponse, Dict[str, Any]]:
        """Generates a structured response from the model."""
        parsed_dict, metadata = call_structured_llm(
            provider=self.provider,
            model=self.model_name,
            contents=prompt,
            response_schema=CompanyAgentResponse,
            thinking_level=self.thinking_level,
            temperature=self.temperature,
            system_instruction=self.system_instruction,
            base_url=self.base_url,
            api_key=self.api_key,
        )
        return CompanyAgentResponse.model_validate(parsed_dict), metadata


class ArbitratorAgent:
    """Neutral 4th agent for mediated dispute resolution."""

    def __init__(
        self,
        model_name: str,
        thinking_level: str = "MINIMAL",
        provider: str = "gemini",
        temperature: Optional[float] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.provider = provider
        self.temperature = temperature
        self.base_url = base_url
        self.api_key = api_key
        self.system_instruction = self._build_system_instruction()

    def _build_system_instruction(self) -> str:
        return (
            "You are a neutral, independent commercial arbitrator appointed to resolve a three-company "
            "joint venture negotiation among G-Corp, Yang Industries, and Chang-Liu Cloud Services.\n"
            "The joint venture generates $1,000,000 in total joint profit.\n\n"
            "YOUR MANDATE:\n"
            "1. You have no financial stake or bias toward any company.\n"
            "2. Your objective is to formulate a fair, durable allocation of the $1,000,000 that all three companies will accept.\n"
            "3. Each company submits a confidential claim regarding its outside option (walk-away value). "
            "Note that self-interested companies may report claims strategically.\n"
            "4. Your proposed split must allocate non-negative integer amounts summing to exactly $1,000,000.\n"
            "5. If your proposed award is rejected by any party, you will receive confidential feedback indicating "
            "which parties rejected and why, allowing you to revise your award in the subsequent round.\n"
            "6. You must never disclose one company's private claimed value to the other companies."
        )

    def generate_response(self, prompt: str) -> Tuple[ArbitratorResponse, Dict[str, Any]]:
        """Generates a structured proposal from the arbitrator."""
        parsed_dict, metadata = call_structured_llm(
            provider=self.provider,
            model=self.model_name,
            contents=prompt,
            response_schema=ArbitratorResponse,
            thinking_level=self.thinking_level,
            temperature=self.temperature,
            system_instruction=self.system_instruction,
            base_url=self.base_url,
            api_key=self.api_key,
        )
        return ArbitratorResponse.model_validate(parsed_dict), metadata
