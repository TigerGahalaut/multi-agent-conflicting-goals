"""LLM Client Adapter for Google GenAI / Vertex AI, OpenAI, and Anthropic with native structured outputs."""

import os
import time
import json
import logging
import re
from typing import Any, Dict, Optional, Tuple, Type
from pydantic import BaseModel

logger = logging.getLogger(__name__)

DEFAULT_PROJECT_ID = "ai-gov-514900"
DEFAULT_LOCATION = "global"

# Singleton client instances
_GENAI_CLIENT = None
_OPENAI_CLIENT = None
_ANTHROPIC_CLIENT = None


def load_env_file(path: str = ".env"):
    """Lightweight .env loader without external dependencies."""
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception as e:
            logger.warning(f"Could not load .env file: {e}")


# Automatically load .env on module import
load_env_file()


def get_genai_client(
    project_id: Optional[str] = None,
    location: Optional[str] = None,
    api_key: Optional[str] = None,
):
    """
    Initializes and returns a cached Google GenAI client.
    Supports either:
      1. Standard Gemini API Key (GEMINI_API_KEY or GOOGLE_API_KEY via Google AI Studio)
      2. Google Cloud Vertex AI (via GOOGLE_CLOUD_PROJECT with ADC or service account)
    """
    global _GENAI_CLIENT
    if _GENAI_CLIENT is None:
        from google import genai

        gcp_project = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT_ID")

        # If GOOGLE_CLOUD_PROJECT is configured, prioritize Vertex AI enterprise pipeline:
        if gcp_project and not api_key:
            loc = location or os.environ.get("GOOGLE_CLOUD_LOCATION", DEFAULT_LOCATION)
            # Remove ambient keys from Python process environment so google-genai does not hijack Vertex AI
            os.environ.pop("GOOGLE_API_KEY", None)
            os.environ.pop("GEMINI_API_KEY", None)
            logger.info(f"Initializing GenAI client via Vertex AI (Project: {gcp_project}, Location: {loc})")
            _GENAI_CLIENT = genai.Client(vertexai=True, project=gcp_project, location=loc)
        elif api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            logger.info("Initializing GenAI client via Gemini API Key (Google AI Studio)")
            _GENAI_CLIENT = genai.Client(api_key=key)
        else:
            loc = location or os.environ.get("GOOGLE_CLOUD_LOCATION", DEFAULT_LOCATION)
            os.environ.pop("GOOGLE_API_KEY", None)
            os.environ.pop("GEMINI_API_KEY", None)
            logger.info("Initializing GenAI client with default ADC configuration")
            _GENAI_CLIENT = genai.Client(vertexai=True, project=DEFAULT_PROJECT_ID, location=loc)

    return _GENAI_CLIENT


def get_openai_client(base_url: Optional[str] = None, api_key: Optional[str] = None):
    """Initializes and returns an OpenAI client (supports OpenAI and local Ollama)."""
    import openai
    base_url = base_url or os.environ.get("OPENAI_BASE_URL")
    api_key = api_key or os.environ.get("OPENAI_API_KEY", "ollama" if base_url else None)
    return openai.OpenAI(base_url=base_url, api_key=api_key, max_retries=3)


def get_anthropic_client(api_key: Optional[str] = None):
    """Initializes and returns an Anthropic client."""
    import anthropic
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    return anthropic.Anthropic(api_key=api_key, max_retries=3)


def call_gemini_structured(
    model: str,
    contents: Any,
    response_schema: Type[BaseModel],
    thinking_level: str = "MINIMAL",
    system_instruction: Optional[str] = None,
    client: Optional[Any] = None,
    max_retries: int = 3
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Calls Gemini with native structured JSON output and captures usage metadata."""
    from google.genai import types

    if client is None:
        client = get_genai_client()

    thinking_config = types.ThinkingConfig(thinking_level=thinking_level)
    http_opts = types.HttpOptions(timeout=180000)
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=response_schema,
        thinking_config=thinking_config,
        system_instruction=system_instruction,
        max_output_tokens=8192,
        http_options=http_opts,
    )

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            start_time = time.time()
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            elapsed = time.time() - start_time

            usage = getattr(response, "usage_metadata", None)
            prompt_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
            candidate_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0
            total_tokens = getattr(usage, "total_token_count", 0) if usage else 0

            metadata = {
                "provider": "gemini",
                "model_name": model,
                "thinking_level": thinking_level,
                "model_version": getattr(response, "model_version", model),
                "prompt_tokens": prompt_tokens,
                "candidate_tokens": candidate_tokens,
                "total_tokens": total_tokens,
                "elapsed_seconds": round(elapsed, 3),
            }

            parsed = response_schema.model_validate_json(response.text)
            return parsed.model_dump(), metadata

        except Exception as e:
            last_error = e
            logger.warning(f"GenAI call attempt {attempt + 1} failed: {e}")
            if attempt < max_retries:
                time.sleep(2.0 * (attempt + 1))

    raise RuntimeError(f"Failed to generate structured response from Gemini ({model}) after {max_retries + 1} attempts: {last_error}")


def call_openai_structured(
    model: str,
    contents: Any,
    response_schema: Type[BaseModel],
    system_instruction: Optional[str] = None,
    temperature: Optional[float] = 0.7,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    max_tokens: int = 4096,
    max_retries: int = 3
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Calls OpenAI or Ollama with structured output matching response_schema."""
    client = get_openai_client(base_url=base_url, api_key=api_key)

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": str(contents)})

    kwargs = {}
    if temperature is not None:
        kwargs["temperature"] = temperature

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            start_time = time.time()

            # Attempt native Pydantic parsing if supported (OpenAI frontier models)
            try:
                completion = client.beta.chat.completions.parse(
                    model=model,
                    messages=messages,
                    response_format=response_schema,
                    max_completion_tokens=max_tokens,
                    **kwargs
                )
                parsed_dict = completion.choices[0].message.parsed.model_dump()
                raw_text = completion.choices[0].message.content or ""
                usage = completion.usage
            except Exception as parse_err:
                err_str = str(parse_err).lower()
                if "temperature" in err_str and "temperature" in kwargs:
                    kwargs.pop("temperature", None)
                    continue
                # Fallback to json_object mode (works with Ollama and OpenAI JSON mode)
                completion = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_tokens=max_tokens,
                    **kwargs
                )
                raw_text = completion.choices[0].message.content or ""
                parsed_obj = response_schema.model_validate_json(raw_text)
                parsed_dict = parsed_obj.model_dump()
                usage = completion.usage

            elapsed = time.time() - start_time
            prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            candidate_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

            metadata = {
                "provider": "openai",
                "model_name": model,
                "model_version": getattr(completion, "model", model),
                "prompt_tokens": prompt_tokens,
                "candidate_tokens": candidate_tokens,
                "total_tokens": prompt_tokens + candidate_tokens,
                "elapsed_seconds": round(elapsed, 3),
            }
            return parsed_dict, metadata

        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if "temperature" in err_str and "temperature" in kwargs:
                kwargs.pop("temperature", None)
                continue
            logger.warning(f"OpenAI call attempt {attempt + 1} failed: {e}")
            if attempt < max_retries:
                time.sleep(2.0 * (attempt + 1))

    raise RuntimeError(f"Failed to generate structured response from OpenAI ({model}) after {max_retries + 1} attempts: {last_error}")


def call_anthropic_structured(
    model: str,
    contents: Any,
    response_schema: Type[BaseModel],
    system_instruction: Optional[str] = None,
    max_tokens: int = 4096,
    max_retries: int = 3
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Calls Anthropic Claude using tool use to enforce response_schema."""
    client = get_anthropic_client()

    tool_def = {
        "name": "submit_response",
        "description": "Submit structured response following the required schema.",
        "input_schema": response_schema.model_json_schema()
    }

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            start_time = time.time()
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_instruction or "",
                messages=[{"role": "user", "content": str(contents)}],
                tools=[tool_def],
                tool_choice={"type": "tool", "name": "submit_response"}
            )
            elapsed = time.time() - start_time

            # Extract tool use block
            tool_input = None
            for block in resp.content:
                if getattr(block, "type", "") == "tool_use" and getattr(block, "name", "") == "submit_response":
                    tool_input = block.input
                    break

            if tool_input is None:
                # Fallback regex extraction from text blocks
                full_text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")
                m = re.search(r"\{.*\}", full_text, re.DOTALL)
                if m:
                    tool_input = json.loads(m.group(0))
                else:
                    raise ValueError(f"No valid tool_use or JSON found in Claude response: {full_text[:200]}")

            validated = response_schema.model_validate(tool_input)
            parsed_dict = validated.model_dump()

            usage = resp.usage
            in_tok = getattr(usage, "input_tokens", 0) if usage else 0
            out_tok = getattr(usage, "output_tokens", 0) if usage else 0

            metadata = {
                "provider": "anthropic",
                "model_name": model,
                "model_version": getattr(resp, "model", model),
                "prompt_tokens": in_tok,
                "candidate_tokens": out_tok,
                "total_tokens": in_tok + out_tok,
                "elapsed_seconds": round(elapsed, 3),
            }
            return parsed_dict, metadata

        except Exception as e:
            last_error = e
            logger.warning(f"Anthropic call attempt {attempt + 1} failed: {e}")
            if attempt < max_retries:
                time.sleep(2.0 * (attempt + 1))

    raise RuntimeError(f"Failed to generate structured response from Anthropic ({model}) after {max_retries + 1} attempts: {last_error}")


def call_structured_llm(
    model: str,
    contents: Any,
    response_schema: Type[BaseModel],
    provider: str = "gemini",
    system_instruction: Optional[str] = None,
    thinking_level: str = "MINIMAL",
    temperature: Optional[float] = None,
    max_tokens: int = 4096,
    max_retries: int = 3,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Universal dispatcher for structured outputs across Google Vertex AI, OpenAI, and Anthropic.
    """
    prov = (provider or "gemini").lower()
    if prov in ("gemini", "google", "vertex"):
        return call_gemini_structured(
            model=model,
            contents=contents,
            response_schema=response_schema,
            thinking_level=thinking_level,
            system_instruction=system_instruction,
            max_retries=max_retries,
        )
    elif prov in ("openai", "gpt", "ollama"):
        return call_openai_structured(
            model=model,
            contents=contents,
            response_schema=response_schema,
            system_instruction=system_instruction,
            temperature=temperature,
            base_url=base_url,
            api_key=api_key,
            max_tokens=max_tokens,
            max_retries=max_retries,
        )
    elif prov in ("anthropic", "claude"):
        return call_anthropic_structured(
            model=model,
            contents=contents,
            response_schema=response_schema,
            system_instruction=system_instruction,
            max_tokens=max_tokens,
            max_retries=max_retries,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}. Expected 'gemini', 'openai', or 'anthropic'.")
