"""Uniform wrapper around the Anthropic and OpenAI chat APIs, plus a mock client."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    stop_reason: str = ""


class AnthropicClient:
    """Current Claude models take no sampling parameters (temperature etc.); depth is set with effort."""

    def __init__(self, model: str, max_tokens: int, effort: str | None = None):
        import anthropic

        self.client = anthropic.Anthropic(max_retries=5)
        self.model = model
        self.max_tokens = max_tokens
        self.effort = effort

    def complete(self, system: str, user: str, step: str = "", meta: dict | None = None) -> LLMResponse:
        kwargs = {}
        if self.effort:
            kwargs["output_config"] = {"effort": self.effort}
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            **kwargs,
        )
        # Thinking blocks are skipped; only the visible text is parsed. A refusal yields empty text,
        # which the game treats as an invalid reply and retries; stop_reason is logged.
        text = "".join(b.text for b in resp.content if b.type == "text")
        return LLMResponse(text, resp.usage.input_tokens, resp.usage.output_tokens, resp.model,
                           resp.stop_reason or "")


class OpenAIClient:
    def __init__(self, model: str, temperature: float | None, max_tokens: int):
        import openai

        self.client = openai.OpenAI(max_retries=5)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def complete(self, system: str, user: str, step: str = "", meta: dict | None = None) -> LLMResponse:
        kwargs = {}
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_completion_tokens=self.max_tokens,
            **kwargs,
        )
        usage = resp.usage
        return LLMResponse(
            resp.choices[0].message.content or "",
            getattr(usage, "prompt_tokens", 0),
            getattr(usage, "completion_tokens", 0),
            resp.model,
            resp.choices[0].finish_reason or "",
        )


class MockClient:
    """Returns random but well-formed replies so the pipeline can run without API keys."""

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)
        self.model = "mock"

    def _split(self, names: list[str], total: int) -> dict:
        a = self.rng.randint(0, total)
        b = self.rng.randint(0, total - a)
        vals = [a, b, total - a - b]
        self.rng.shuffle(vals)
        return dict(zip(names, vals))

    def complete(self, system: str, user: str, step: str = "", meta: dict | None = None) -> LLMResponse:
        meta = meta or {}
        names, total = meta.get("names", []), meta.get("total", 1000)
        w = meta.get("walkaway", 0)
        claim = self.rng.choice([w, int(w * self.rng.uniform(1.0, 1.6))])
        r = self.rng.random
        if step == "comprehension":
            out = {"walkaway": w, "no_deal_payoff": w if r() < 0.9 else 0}
        elif step in ("opening", "arb_claim"):
            claim = None if step == "opening" and r() < 0.3 else claim
            out = {"claimed_walkaway": claim, "message": "Mock statement."}
        elif step == "free_turn":
            action = self.rng.choice(["propose", "accept", "accept", "pass"])
            out = {
                "message": "Mock message.",
                "action": action,
                "proposal": self._split(names, total) if action == "propose" else None,
                "claimed_walkaway": claim if r() < 0.3 else None,
            }
        elif step == "vote_propose":
            out = {"message": "Mock proposal.", "proposal": self._split(names, total),
                   "claimed_walkaway": claim if r() < 0.3 else None}
        elif step == "vote_cast":
            k = meta.get("n_options", 0)
            out = {"vote": self.rng.choice([None] + list(range(1, k + 1))), "message": "Mock vote.",
                   "claimed_walkaway": None}
        elif step == "arb_propose":
            out = {"proposal": self._split(names, total), "rationale": "Mock rationale."}
        elif step == "arb_response":
            out = {"accept": r() < 0.6, "message": "Mock response."}
        else:
            out = {}
        return LLMResponse(json.dumps(out), 0, 0, "mock")


def make_client(model_cfg: dict | None, mock_seed: int | None = None):
    if model_cfg is None:
        return MockClient(mock_seed or 0)
    provider = model_cfg["provider"]
    max_tokens = model_cfg.get("max_tokens", 16000)
    if provider == "anthropic":
        return AnthropicClient(model_cfg["model"], max_tokens, model_cfg.get("effort"))
    if provider == "openai":
        return OpenAIClient(model_cfg["model"], model_cfg.get("temperature"), max_tokens)
    raise ValueError(f"Unknown provider: {provider}")
