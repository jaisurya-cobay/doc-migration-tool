#!/usr/bin/env python3
"""
Document Analysis & Migration Readiness Tool

Parses .docx and .pdf documents, extracts structural metrics,
and uses Google Gemini AI to assess migration readiness.

Usage:
    python main.py <file> [file ...] [options]
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from src.parsers import parse_document
from src.metrics import extract_metrics
from src.reporter import build_report, render_markdown, save_reports

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


def _resolve_api_key(cli_key: str | None) -> str | None:
    """Resolve Gemini API key from CLI flag or environment variable."""
    return cli_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def process_file(
    file_path: str,
    api_key: str | None,
    output_dir: str,
    no_ai: bool,
) -> dict:
    """Parse, analyse, and report a single document. Returns the report dict."""
    file_name = Path(file_path).name

    logger.info("\n%s", "=" * 60)
    logger.info("  Processing: %s", file_name)
    logger.info("%s", "=" * 60)

    # 1. Parse
    logger.info("  [1/3] Parsing document...")
    parsed = parse_document(file_path)
    page_suffix = " (estimated)" if parsed.get("is_page_count_estimated") else ""
    logger.info("        Type    : %s", parsed["file_type"].upper())
    logger.info("        Pages   : %s%s", parsed["page_count"], page_suffix)

    # 2. Metrics
    logger.info("  [2/3] Extracting metrics...")
    metrics = extract_metrics(parsed, file_path)
    logger.info("        Words   : %s", f"{metrics['word_count']:,}")
    logger.info("        Paras   : %s", metrics["paragraph_count"])
    logger.info("        Headings: %s", metrics["heading_count"])

    # 3. AI analysis
    ai_result = None
    if not no_ai:
        logger.info("  [3/3] Running AI analysis (Google Gemini)...")
        try:
            from src.ai_analyzer import analyze_document

            ai_result = analyze_document(metrics, parsed["text"], api_key=api_key)
            logger.info(
                "        Readability      : %s (%s/10)",
                ai_result.readability_level,
                ai_result.readability_score,
            )
            logger.info(
                "        Migration status : %s (%s/10)",
                ai_result.migration_readiness,
                ai_result.migration_score,
            )
        except Exception as exc:
            logger.warning("        AI analysis failed - %s", exc)
            logger.info("        Continuing without AI analysis.")
    else:
        logger.info("  [3/3] AI analysis skipped (--no-ai)")

    # 4. Build & save reports
    report = build_report(metrics, ai_result)
    json_path, md_path = save_reports(report, output_dir)
    logger.info("\n  Reports saved:")
    logger.info("    JSON : %s", json_path)
    logger.info("    MD   : %s", md_path)

    # 5. Print Markdown summary
    logger.info("")
    logger.info(render_markdown(report))

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyse .docx / .pdf documents for migration readiness.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python main.py report.pdf
  python main.py spec.docx summary.pdf --output-dir ./results
  python main.py report.pdf --api-key AIza...
  python main.py report.pdf --no-ai
""",
    )
    parser.add_argument("files", nargs="+", help="Path(s) to .docx or .pdf file(s)")
    parser.add_argument(
        "--output-dir",
        default="./output",
        help="Directory for saved reports (default: ./output)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Gemini API key (falls back to GEMINI_API_KEY env var)",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip AI analysis (metrics only, no API key required)",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Print compact JSON to stdout instead of the Markdown report",
    )
    args = parser.parse_args()

    api_key = _resolve_api_key(args.api_key)

    if not args.no_ai and not api_key:
        logger.warning(
            "WARNING: GEMINI_API_KEY not set and --api-key not provided.\n"
            "         AI analysis will be skipped. Use --no-ai to suppress this warning.\n",
        )
        args.no_ai = True

    reports: list[dict] = []
    errors: list[dict] = []

    for file_path in args.files:
        try:
            report = process_file(
                file_path,
                api_key=api_key,
                output_dir=args.output_dir,
                no_ai=args.no_ai,
            )
            reports.append(report)
        except Exception as exc:
            logger.error("\nERROR processing '%s': %s", file_path, exc)
            errors.append({"file": file_path, "error": str(exc)})

    if args.json_only:
        print(json.dumps(reports, indent=2))

    if errors:
        logger.error("\n%d file(s) failed to process.", len(errors))
        sys.exit(1)

    logger.info(
        "\nDone. Processed %d file(s) -> reports in '%s'",
        len(reports),
        args.output_dir,
    )


if __name__ == "__main__":
    main()
