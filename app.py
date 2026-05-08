"""Flask web app for Document Analysis & Migration Readiness Tool."""

import json
import os
import tempfile
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file

from src.parsers import parse_document
from src.metrics import extract_metrics
from src.ai_analyzer import analyze_document
from src.reporter import build_report, render_markdown, save_reports

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB max total upload

OUTPUT_DIR = "./output"
ALLOWED_EXTENSIONS = {"pdf", "docx"}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _process_single_file(file, api_key: str, skip_ai: bool) -> dict:
    """Process a single uploaded file and return the result dict."""
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        parsed = parse_document(tmp_path)
        metrics = extract_metrics(parsed, tmp_path)
        metrics["file_name"] = file.filename

        ai_result = None
        ai_data = None
        env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        if not skip_ai and (api_key or env_key):
            try:
                ai_result = analyze_document(metrics, parsed["text"], api_key=api_key or None)
                ai_data = ai_result.model_dump()
            except Exception as e:
                ai_data = {"error": str(e)}

        report = build_report(metrics, ai_result)
        markdown_summary = render_markdown(report)
        json_path, md_path = save_reports(report, OUTPUT_DIR)

        return {
            "success": True,
            "file_name": file.filename,
            "metrics": metrics,
            "ai_analysis": ai_data,
            "summary_report": markdown_summary,
            "saved_files": {"json": json_path, "markdown": md_path},
        }
    except Exception as e:
        return {
            "success": False,
            "file_name": file.filename,
            "error": str(e),
        }
    finally:
        os.unlink(tmp_path)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    files = request.files.getlist("file")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files uploaded"}), 400

    api_key = request.form.get("api_key", "").strip()
    skip_ai = request.form.get("skip_ai") == "true"

    # Filter valid files
    valid_files = [f for f in files if f.filename and _allowed_file(f.filename)]
    invalid_files = [f.filename for f in files if f.filename and not _allowed_file(f.filename)]

    if not valid_files:
        return jsonify({"error": "No valid .pdf or .docx files found"}), 400

    results = []
    for file in valid_files:
        result = _process_single_file(file, api_key, skip_ai)
        results.append(result)

    return jsonify({
        "results": results,
        "total": len(valid_files),
        "succeeded": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "skipped_files": invalid_files,
    })


@app.route("/download/<file_type>/<filename>")
def download_report(file_type, filename):
    """Download a saved report file."""
    safe_name = Path(filename).name
    if file_type not in ("json", "md"):
        return "Invalid file type", 400

    path = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.exists(path):
        return "File not found", 404

    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
