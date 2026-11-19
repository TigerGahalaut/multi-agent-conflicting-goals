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
        import os
        import anthropic

        # A per-request timeout (seconds) so a stalled connection is retried instead of blocking for the
        # SDK default of 10 minutes per attempt.
        self.client = anthropic.Anthropic(max_retries=5, timeout=float(os.environ.get("ANTHROPIC_TIMEOUT", "120")))
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


class GeminiClient:
    """Client for Google Vertex AI Gemini models using google-genai SDK with exponential backoff."""

    def __init__(self, model: str, max_tokens: int = 8192, thinking_level: str | None = None,
                 project: str = "ai-gov-514900", location: str = "global", max_retries: int = 5):
        import os
        from google import genai
        from google.genai import types

        # A per-request timeout (ms) so a stalled request raises and the retry loop below can recover.
        http = types.HttpOptions(timeout=int(os.environ.get("GEMINI_TIMEOUT_MS", "120000")))
        # Credentials, first match wins: a Vertex AI express-mode key, a Gemini API (AI Studio) key,
        # else Vertex AI with Application Default Credentials (GOOGLE_CLOUD_PROJECT overrides the project).
        vertex_key = os.environ.get("VERTEX_API_KEY")
        studio_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if vertex_key:
            self.client = genai.Client(vertexai=True, api_key=vertex_key, http_options=http)
        elif studio_key:
            self.client = genai.Client(api_key=studio_key, http_options=http)
        else:
            self.client = genai.Client(vertexai=True, project=os.environ.get("GOOGLE_CLOUD_PROJECT", project),
                                       location=location, http_options=http)
        self.model = model
        self.max_tokens = max_tokens
        self.thinking_level = thinking_level
        self.max_retries = max_retries

    def complete(self, system: str, user: str, step: str = "", meta: dict | None = None) -> LLMResponse:
        import time
        from google.genai import types

        config_kwargs = {
            "system_instruction": system,
            "response_mime_type": "application/json",
            "max_output_tokens": self.max_tokens,
        }
        if self.thinking_level:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=self.thinking_level)

        import os
        import re

        # Optional client-side pacing (seconds between calls), e.g. GEMINI_MIN_INTERVAL=4.2 keeps one process
        # under a 15 requests-per-minute free-tier quota.
        min_gap = float(os.environ.get("GEMINI_MIN_INTERVAL", "0"))
        last_exc = None
        attempts = max(self.max_retries, int(os.environ.get("GEMINI_MAX_RETRIES", "0")))
        for attempt in range(attempts + 1):
            wait = getattr(self, "_last_call", 0) + min_gap - time.time()
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.time()
            try:
                resp = self.client.models.generate_content(
                    model=self.model,
                    contents=user,
                    config=types.GenerateContentConfig(**config_kwargs),
                )

                usage = getattr(resp, "usage_metadata", None)
                in_tok = getattr(usage, "prompt_token_count", 0) if usage else 0
                out_tok = getattr(usage, "candidates_token_count", 0) if usage else 0
                model_version = getattr(resp, "model_version", self.model) or self.model

                return LLMResponse(
                    resp.text or "",
                    in_tok,
                    out_tok,
                    model_version,
                    "stop",
                )
            except Exception as e:
                last_exc = e
                if attempt < attempts:
                    delay = min(3.0 * (2 ** attempt), 60.0)  # 3s, 6s, 12s, 24s, 48s, then 60s
                    hinted = re.search(r"retry in ([0-9.]+)s", str(e))  # 429s say how long to wait
                    if hinted:
                        delay = max(delay, float(hinted.group(1)) + 1.0)
                    print(f"\n[GeminiClient] {str(e)[:120]} ... retrying in {delay:.0f}s "
                          f"(attempt {attempt + 1}/{attempts})", flush=True)
                    time.sleep(delay)

        raise last_exc


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
    if provider in ("gemini", "google", "vertex"):
        return GeminiClient(
            model_cfg["model"],
            max_tokens,
            model_cfg.get("thinking_level"),
            project=model_cfg.get("project", "ai-gov-514900"),
            location=model_cfg.get("location", "global"),
        )
    raise ValueError(f"Unknown provider: {provider}")
