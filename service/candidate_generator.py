"""Candidate generation utilities for SQL optimization."""

from google.genai import types


def clean_markdown_sql(text: str) -> str:
    """Strip markdown code fences from model output when present."""
    if text is None:
        return ""

    cleaned = text.strip()
    if "```" not in cleaned:
        return cleaned

    parts = cleaned.split("```")
    if len(parts) < 2:
        return cleaned

    fenced = parts[1].strip()
    if fenced.lower().startswith("sql"):
        fenced = fenced[3:].strip()
    return fenced


def generate_candidate(
    client,
    prompt: str,
    system_prompt: str,
    temperature: float = 0.1,
    model: str = "gemini-2.5-flash",
) -> str:
    """Generate one SQL candidate from the configured model."""
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
        ),
    )
    response_text = (response.text or "").strip()
    return clean_markdown_sql(response_text)

