"""AI-driven document analysis using Google Gemini (default) or Anthropic Claude."""

import json
import logging
import os
import re
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AIAnalysis(BaseModel):
    """Structured result of the AI migration-readiness assessment."""

    readability_level: str = Field(description="Easy | Medium | Complex")
    readability_score: int = Field(ge=1, le=10, description="1-10 readability score")
    content_clarity: str = Field(description="Narrative assessment of clarity and consistency")
    structural_quality: str = Field(description="Well-Organized | Moderately-Organized | Fragmented")
    migration_readiness: str = Field(description="Ready | Needs Minor Cleanup | Requires Restructuring")
    migration_score: int = Field(ge=1, le=10, description="1-10 migration readiness score")
    estimated_migration_effort: str = Field(description="Low | Medium | High")
    strengths: list[str] = Field(description="List of document strengths")
    issues: list[str] = Field(description="List of issues found")
    suggestions: list[str] = Field(description="Actionable improvement suggestions")
    summary: str = Field(description="2-3 sentence overall assessment")


_SYSTEM_PROMPT = (
    "You are a documentation migration specialist. Your job is to assess documents "
    "for migration into platforms like Document360, Confluence, or similar knowledge bases. "
    "Respond ONLY with valid JSON that matches the specified schema. "
    "Do not include any prose, markdown fences, or extra text."
)

_USER_TEMPLATE = """\
Analyse the following document and return a JSON object that exactly matches this schema:

{{
  "readability_level": "<Easy|Medium|Complex>",
  "readability_score": <integer 1-10>,
  "content_clarity": "<concise assessment of clarity and consistency>",
  "structural_quality": "<Well-Organized|Moderately-Organized|Fragmented>",
  "migration_readiness": "<Ready|Needs Minor Cleanup|Requires Restructuring>",
  "migration_score": <integer 1-10>,
  "estimated_migration_effort": "<Low|Medium|High>",
  "strengths": ["<strength 1>", "..."],
  "issues": ["<issue 1>", "..."],
  "suggestions": ["<actionable suggestion 1>", "..."],
  "summary": "<2-3 sentence overall assessment>"
}}

--- DOCUMENT METRICS ---
File: {file_name}
Type: {file_type}
Pages: {page_count}{page_note}
Words: {word_count}
Paragraphs: {paragraph_count}
Headings/Sections: {heading_count}
Avg words per paragraph: {avg_words_per_paragraph}
Tables: {table_count}
Images: {image_count}
Vocabulary richness: {vocabulary_richness} (0=repetitive, 1=highly varied)
Max heading depth: {max_heading_depth}

--- CONTENT SAMPLE (first 3000 chars) ---
{text_sample}
"""


def _build_prompt(metrics: dict, full_text: str) -> str:
    """Format the analysis prompt with document metrics and a content sample."""
    page_note = " (estimated)" if metrics.get("is_page_count_estimated") else ""
    return _USER_TEMPLATE.format(
        file_name=metrics["file_name"],
        file_type=metrics["file_type"].upper(),
        page_count=metrics["page_count"],
        page_note=page_note,
        word_count=metrics["word_count"],
        paragraph_count=metrics["paragraph_count"],
        heading_count=metrics["heading_count"],
        avg_words_per_paragraph=metrics["avg_words_per_paragraph"],
        table_count=metrics["table_count"],
        image_count=metrics["image_count"],
        vocabulary_richness=metrics["vocabulary_richness"],
        max_heading_depth=metrics["max_heading_depth"],
        text_sample=full_text[:3000].strip(),
    )


def _parse_json_response(raw: str) -> dict:
    """Extract and parse JSON from an LLM response, handling markdown fences."""
    raw = raw.strip()

    # Try to extract JSON from markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL)
    if fence_match:
        raw = fence_match.group(1).strip()

    # Fallback: find the first { ... } block
    if not raw.startswith("{"):
        brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if brace_match:
            raw = brace_match.group(0)

    return json.loads(raw)


# -- Gemini (default) ---------------------------------------------------------

GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"]
MAX_RETRIES = 3
RETRY_DELAY_SEC = 5


def _analyze_with_gemini(metrics: dict, full_text: str, api_key: Optional[str]) -> AIAnalysis:
    """Run analysis using Google Gemini with automatic model fallback and retry."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise ImportError(
            "google-genai is not installed. Run: pip install google-genai"
        )

    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError(
            "Gemini API key not found. "
            "Set the GEMINI_API_KEY environment variable or pass --api-key."
        )

    client = genai.Client(api_key=key)
    prompt = _build_prompt(metrics, full_text)
    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_PROMPT,
        response_mime_type="application/json",
        temperature=0.2,
    )

    last_error = None
    for model_name in GEMINI_MODELS:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info("        Trying %s (attempt %d/%d)...", model_name, attempt, MAX_RETRIES)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
                data = _parse_json_response(response.text)
                return AIAnalysis(**data)
            except Exception as exc:
                last_error = exc
                err_str = str(exc)
                # Retry on 429 (rate limit) or 503 (overloaded)
                if "429" in err_str or "503" in err_str:
                    if attempt < MAX_RETRIES:
                        import time
                        time.sleep(RETRY_DELAY_SEC * attempt)
                        continue
                    # Exhausted retries for this model — try next model
                    logger.info("        %s exhausted retries, trying next model...", model_name)
                    break
                else:
                    raise  # Non-retryable error, raise immediately

    raise last_error  # type: ignore[misc]


# -- Claude (optional) --------------------------------------------------------

def _analyze_with_claude(metrics: dict, full_text: str, api_key: Optional[str]) -> AIAnalysis:
    """Run analysis using Anthropic Claude Opus 4.6."""
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "anthropic is not installed. Run: pip install anthropic"
        )

    client = anthropic.Anthropic(
        api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
    )
    prompt = _build_prompt(metrics, full_text)

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_json = next(
        (block.text for block in response.content if block.type == "text"), ""
    )
    data = _parse_json_response(raw_json)
    return AIAnalysis(**data)


# -- Public API ---------------------------------------------------------------

_PROVIDERS = {
    "gemini": _analyze_with_gemini,
    "claude": _analyze_with_claude,
}


def analyze_document(
    metrics: dict,
    full_text: str,
    provider: str = "gemini",
    api_key: Optional[str] = None,
) -> AIAnalysis:
    """Analyse a document for migration readiness using the chosen AI provider.

    Args:
        metrics:   Output of ``extract_metrics()``.
        full_text: Full document text.
        provider:  ``"gemini"`` (default) or ``"claude"``.
        api_key:   API key override (falls back to env vars).

    Returns:
        An ``AIAnalysis`` instance with structured results.

    Raises:
        ValueError: If the provider name is unknown.
    """
    provider = provider.lower().strip()
    handler = _PROVIDERS.get(provider)
    if handler is None:
        raise ValueError(
            f"Unknown provider '{provider}'. Choose from: {', '.join(_PROVIDERS)}"
        )
    return handler(metrics, full_text, api_key)
