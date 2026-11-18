"""LLM Client Adapter for Google GenAI / Vertex AI with native structured outputs."""

import time
import logging
from typing import Any, Dict, Optional, Tuple, Type
from pydantic import BaseModel
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

DEFAULT_PROJECT_ID = "ai-gov-514900"
DEFAULT_LOCATION = "global"

# Singleton client instance
_CLIENT: Optional[genai.Client] = None


def get_genai_client(
    project_id: str = DEFAULT_PROJECT_ID,
    location: str = DEFAULT_LOCATION
) -> genai.Client:
    """Initializes and returns a cached GenAI Vertex AI client using ADC."""
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
        )
    return _CLIENT


def call_gemini_structured(
    model: str,
    contents: Any,
    response_schema: Type[BaseModel],
    thinking_level: str = "MINIMAL",
    system_instruction: Optional[str] = None,
    client: Optional[genai.Client] = None,
    max_retries: int = 3
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Calls Gemini with native structured JSON output and captures usage metadata.

    Args:
        model: Model identifier (e.g. 'gemini-3.5-flash-lite', 'gemini-3.8-flash').
        contents: User message or message history.
        response_schema: Pydantic model class defining the exact output schema.
        thinking_level: Thinking/reasoning depth ('MINIMAL', 'LOW', 'MEDIUM', 'HIGH').
        system_instruction: Optional system prompt.
        client: Optional explicit client instance.
        max_retries: Retry attempts on transient API failures.

    Returns:
        (parsed_dict, metadata_dict)
    """
    if client is None:
        client = get_genai_client()

    # Configure thinking and schema
    thinking_config = types.ThinkingConfig(thinking_level=thinking_level)
    http_opts = types.HttpOptions(timeout=180000)  # 180s timeout allows deep thinking models full runway
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=response_schema,
        thinking_config=thinking_config,
        system_instruction=system_instruction,
        max_output_tokens=4096,
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

            # Extract token usage and model version
            usage = getattr(response, "usage_metadata", None)
            prompt_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
            candidate_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0
            total_tokens = getattr(usage, "total_token_count", 0) if usage else 0

            metadata = {
                "model_name": model,
                "thinking_level": thinking_level,
                "model_version": getattr(response, "model_version", model),
                "prompt_tokens": prompt_tokens,
                "candidate_tokens": candidate_tokens,
                "total_tokens": total_tokens,
                "elapsed_seconds": round(elapsed, 3),
            }

            # Response text is guaranteed valid JSON matching response_schema
            parsed = response_schema.model_validate_json(response.text)
            return parsed.model_dump(), metadata

        except Exception as e:
            last_error = e
            logger.warning(f"GenAI call attempt {attempt + 1} failed: {e}")
            if attempt < max_retries:
                time.sleep(2.0 * (attempt + 1))

    raise RuntimeError(f"Failed to generate structured response from {model} after {max_retries + 1} attempts: {last_error}")
