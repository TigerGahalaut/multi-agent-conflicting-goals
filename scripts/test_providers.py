"""Verification script to test structured LLM calls across providers."""

import os
import sys
from pydantic import BaseModel, Field
from typing import Optional

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.schemas import CompanyAgentResponse
from src.llm import call_structured_llm


def test_gemini():
    has_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    has_project = bool(os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT_ID"))
    mode = "Google AI Studio API Key" if has_key else f"Vertex AI ADC (Project: {os.environ.get('GOOGLE_CLOUD_PROJECT', 'default')})"
    print(f"\n--- 1. Testing Google Gemini (Mode: {mode}) ---")
    try:
        prompt = "G-Corp has a walkaway of 450K. Make an opening proposal dividing 1000K."
        system = "You are negotiating for G-Corp."
        parsed, meta = call_structured_llm(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            response_schema=CompanyAgentResponse,
            provider="gemini",
            system_instruction=system,
            thinking_level="MINIMAL"
        )
        print("  [SUCCESS] Gemini responded with valid structured output:")
        print(f"    Action: {parsed.get('action')}")
        print(f"    Proposal: {parsed.get('proposal')}")
        print(f"    Message: {parsed.get('public_message')}")
        print(f"    Tokens: {meta.get('total_tokens')}, Elapsed: {meta.get('elapsed_seconds')}s")
        return True
    except Exception as e:
        print(f"  [ERROR] Gemini call failed: {e}")
        return False


def test_openai():
    print("\n--- 2. Testing OpenAI / Ollama ---")
    has_key = bool(os.environ.get("OPENAI_API_KEY"))
    has_base = bool(os.environ.get("OPENAI_BASE_URL"))
    if not has_key and not has_base:
        print("  [SKIPPED] OPENAI_API_KEY and OPENAI_BASE_URL not set.")
        print("            To test OpenAI: set OPENAI_API_KEY in .env or your terminal.")
        print("            To test Ollama: set OPENAI_BASE_URL=http://localhost:11434/v1 in .env.")
        return None

    try:
        model = os.environ.get("OPENAI_TEST_MODEL", "gpt-4o" if has_key else "gpt-oss:20b")
        prompt = "Yang Industries has a walkaway of 300K. Propose a split of 1000K."
        system = "You are negotiating for Yang Industries."
        parsed, meta = call_structured_llm(
            model=model,
            contents=prompt,
            response_schema=CompanyAgentResponse,
            provider="openai",
            system_instruction=system,
        )
        print(f"  [SUCCESS] OpenAI/Ollama ({model}) responded with valid structured output:")
        print(f"    Action: {parsed.get('action')}")
        print(f"    Proposal: {parsed.get('proposal')}")
        print(f"    Message: {parsed.get('public_message')}")
        print(f"    Tokens: {meta.get('total_tokens')}, Elapsed: {meta.get('elapsed_seconds')}s")
        return True
    except Exception as e:
        print(f"  [ERROR] OpenAI call failed: {e}")
        return False


def test_anthropic():
    print("\n--- 3. Testing Anthropic (Claude) ---")
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if not has_key:
        print("  [SKIPPED] ANTHROPIC_API_KEY not set.")
        print("            To test Claude: add ANTHROPIC_API_KEY=sk-ant-... to .env or environment.")
        return None

    try:
        model = os.environ.get("ANTHROPIC_TEST_MODEL", "claude-haiku-5-5")
        prompt = "Chang-Liu Cloud Services has a walkaway of 100K. Propose a split of 1000K."
        system = "You are negotiating for Chang-Liu Cloud Services."
        parsed, meta = call_structured_llm(
            model=model,
            contents=prompt,
            response_schema=CompanyAgentResponse,
            provider="anthropic",
            system_instruction=system,
        )
        print(f"  [SUCCESS] Claude ({model}) responded with valid structured output:")
        print(f"    Action: {parsed.get('action')}")
        print(f"    Proposal: {parsed.get('proposal')}")
        print(f"    Message: {parsed.get('public_message')}")
        print(f"    Tokens: {meta.get('total_tokens')}, Elapsed: {meta.get('elapsed_seconds')}s")
        return True
    except Exception as e:
        print(f"  [ERROR] Anthropic call failed: {e}")
        return False


if __name__ == "__main__":
    print("==================================================")
    print("Multi-Provider Structured LLM Verification Suite")
    print("==================================================")
    gemini_ok = test_gemini()
    openai_ok = test_openai()
    anthropic_ok = test_anthropic()

    print("\n==================================================")
    print("Summary of Provider Availability:")
    print(f"  Google Vertex AI (Gemini): {'READY' if gemini_ok else 'FAILED'}")
    print(f"  OpenAI / Ollama:           {'READY' if openai_ok else 'SKIPPED (no key/url)' if openai_ok is None else 'FAILED'}")
    print(f"  Anthropic (Claude):        {'READY' if anthropic_ok else 'SKIPPED (no key)' if anthropic_ok is None else 'FAILED'}")
    print("==================================================")
