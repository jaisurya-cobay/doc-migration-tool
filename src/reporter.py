"""Generate JSON and Markdown summary reports."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def build_report(metrics: dict, ai: object | None) -> dict:
    """Combine metrics and AI analysis into a single report dict."""
    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "document_metrics": metrics,
    }

    if ai:
        report["ai_analysis"] = {
            "readability_level": ai.readability_level,
            "readability_score": ai.readability_score,
            "content_clarity": ai.content_clarity,
            "structural_quality": ai.structural_quality,
            "migration_readiness": ai.migration_readiness,
            "migration_score": ai.migration_score,
            "estimated_migration_effort": ai.estimated_migration_effort,
            "strengths": ai.strengths,
            "issues": ai.issues,
            "suggestions": ai.suggestions,
            "summary": ai.summary,
        }
    else:
        report["ai_analysis"] = None

    return report


def render_markdown(report: dict) -> str:
    """Render the report as a human-readable Markdown summary."""
    m = report["document_metrics"]
    ai = report.get("ai_analysis")

    page_note = " *(estimated)*" if m.get("is_page_count_estimated") else ""
    lines = [
        f"# Migration Readiness Report - {m['file_name']}",
        "",
        f"*Generated: {report['generated_at']}*",
        "",
        "---",
        "",
        "## Document Metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| File type | {m['file_type'].upper()} |",
        f"| File size | {m['file_size_kb']} KB |",
        f"| Pages | {m['page_count']}{page_note} |",
        f"| Words | {m['word_count']:,} |",
        f"| Characters | {m['char_count']:,} |",
        f"| Sentences | {m['sentence_count']} |",
        f"| Paragraphs | {m['paragraph_count']} |",
        f"| Headings/Sections | {m['heading_count']} |",
        f"| Max heading depth | {m['max_heading_depth']} |",
        f"| Avg words/paragraph | {m['avg_words_per_paragraph']} |",
        f"| Unique words | {m['unique_words']:,} |",
        f"| Vocabulary richness | {m['vocabulary_richness']} |",
        f"| Tables | {m['table_count']} |",
        f"| Images | {m['image_count']} |",
        f"| Code blocks | {m['code_block_count']} |",
        f"| URLs/links | {m['url_count']} |",
        f"| Est. reading time | {m['estimated_reading_time_min']} min |",
        "",
    ]

    if ai:
        r_score = ai["readability_score"]
        m_score = ai["migration_score"]

        lines += [
            "---",
            "",
            "## AI Analysis",
            "",
            "| Dimension | Assessment |",
            "|-----------|------------|",
            f"| Readability | **{ai['readability_level']}** ({r_score}/10) |",
            f"| Structural quality | **{ai['structural_quality']}** |",
            f"| Migration readiness | **{ai['migration_readiness']}** ({m_score}/10) |",
            f"| Migration effort | **{ai['estimated_migration_effort']}** |",
            "",
            "### Content Clarity",
            "",
            ai["content_clarity"],
            "",
        ]

        if ai["strengths"]:
            lines.append("### Strengths")
            lines.append("")
            for s in ai["strengths"]:
                lines.append(f"- {s}")
            lines.append("")

        if ai["issues"]:
            lines.append("### Issues Found")
            lines.append("")
            for issue in ai["issues"]:
                lines.append(f"- {issue}")
            lines.append("")

        if ai["suggestions"]:
            lines.append("### Improvement Suggestions")
            lines.append("")
            for i, sug in enumerate(ai["suggestions"], 1):
                lines.append(f"{i}. {sug}")
            lines.append("")

        lines += [
            "### Summary",
            "",
            ai["summary"],
            "",
        ]
    else:
        lines += [
            "---",
            "",
            "*AI analysis was skipped (use `--api-key` or set `GEMINI_API_KEY`).*",
            "",
        ]

    return "\n".join(lines)


def save_reports(report: dict, output_dir: str) -> tuple[str, str]:
    """Save JSON and Markdown reports. Returns (json_path, md_path)."""
    os.makedirs(output_dir, exist_ok=True)

    stem = Path(report["document_metrics"]["file_name"]).stem
    json_path = os.path.join(output_dir, f"{stem}_report.json")
    md_path = os.path.join(output_dir, f"{stem}_report.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(report))

    return json_path, md_path
