"""Extract structural and content-level metrics from a parsed document."""

import re
from pathlib import Path


def extract_metrics(parsed: dict, file_path: str) -> dict:
    """Compute all document metrics from parsed content.

    Args:
        parsed:    Output of ``parse_document()``.
        file_path: Original file path (for file-level metadata).

    Returns:
        A flat dict of all computed metrics.
    """
    text: str = parsed.get("text", "")
    paragraphs: list = parsed.get("paragraphs", [])
    headings: list = parsed.get("headings", [])

    words = text.split()
    word_count = len(words)
    char_count = len(text)
    paragraph_count = len(paragraphs)
    heading_count = len(headings)

    # Sentence count (approximate: split on terminal punctuation)
    sentence_count = len(re.findall(r"[.!?]+", text))

    # Average words per paragraph
    para_word_counts = [len(p.split()) for p in paragraphs if p.strip()]
    avg_words_per_para = (
        round(sum(para_word_counts) / len(para_word_counts), 1)
        if para_word_counts
        else 0.0
    )

    # Vocabulary richness (type-token ratio)
    unique_words = len({w.lower().strip(".,;:\"'()[]") for w in words})
    vocab_richness = round(unique_words / word_count, 3) if word_count else 0.0

    # Estimated reading time at 200 wpm
    reading_time_min = round(word_count / 200, 1)

    # Maximum heading depth present
    max_heading_depth = max((h.get("level", 1) for h in headings), default=0)

    # Inline code / code blocks
    code_block_count = len(re.findall(r"```|~~~|`[^`]+`", text))

    # URLs / hyperlinks
    url_count = len(re.findall(r"https?://\S+", text))

    # File metadata
    path = Path(file_path)
    file_size_kb = round(path.stat().st_size / 1024, 1) if path.exists() else 0

    return {
        "file_name": path.name,
        "file_type": parsed.get("file_type", "unknown"),
        "file_size_kb": file_size_kb,
        "page_count": parsed.get("page_count", 0),
        "is_page_count_estimated": parsed.get("is_page_count_estimated", False),
        "word_count": word_count,
        "char_count": char_count,
        "sentence_count": sentence_count,
        "paragraph_count": paragraph_count,
        "heading_count": heading_count,
        "avg_words_per_paragraph": avg_words_per_para,
        "max_heading_depth": max_heading_depth,
        "unique_words": unique_words,
        "vocabulary_richness": vocab_richness,
        "table_count": parsed.get("table_count", 0),
        "image_count": parsed.get("image_count", 0),
        "code_block_count": code_block_count,
        "url_count": url_count,
        "estimated_reading_time_min": reading_time_min,
    }
