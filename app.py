"""Flask web app for Document Analysis & Migration Readiness Tool."""

import json
import os
import tempfile
from pathlib import Path

from flask import Flask, render_template, request, jsonify

from src.parsers import parse_document
from src.metrics import extract_metrics
from src.ai_analyzer import analyze_document

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB max upload

ALLOWED_EXTENSIONS = {"pdf", "docx"}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    # Validate file
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "" or not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": "Only .pdf and .docx files are supported"}), 400

    api_key = request.form.get("api_key", "").strip()
    env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    skip_ai = request.form.get("skip_ai") == "true"

    # Save to temp file
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        # 1. Parse
        parsed = parse_document(tmp_path)

        # 2. Metrics
        metrics = extract_metrics(parsed, tmp_path)
        metrics["file_name"] = file.filename  # Use original name

        # 3. AI Analysis
        ai_data = None
        if not skip_ai and (api_key or env_key):
            try:
                ai_result = analyze_document(metrics, parsed["text"], api_key=api_key or None)
                ai_data = ai_result.model_dump()
            except Exception as e:
                ai_data = {"error": str(e)}

        return jsonify({
            "success": True,
            "metrics": metrics,
            "ai_analysis": ai_data,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
