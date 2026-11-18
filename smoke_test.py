"""Smoke test: verify Gemini inference works via ADC (Application Default Credentials).
No API key needed — uses the credentials from `gcloud auth application-default login`.
"""
from google import genai

PROJECT_ID = "ai-gov-514900"
MODEL_ID = "gemini-3.5-flash-lite"  # Cheapest available model

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location="global",
)

response = client.models.generate_content(
    model=MODEL_ID,
    contents="Reply with exactly: GCP inference works.",
    config={"max_output_tokens": 256},
)
print(response.text)
