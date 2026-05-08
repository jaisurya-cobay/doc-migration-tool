# Document Analysis & Migration Readiness Tool

Analyses `.docx` and `.pdf` documents, extracts structural metrics, and uses **Google Gemini AI** to produce an actionable migration-readiness assessment for platforms like Document360.

---

## Tools & Libraries

| Library | Purpose |
|---------|---------|
| `google-genai` | Google Gemini 2.5 Flash API for AI analysis |
| `python-docx` | Parse Microsoft Word (.docx) documents |
| `pdfplumber` | Parse PDF documents (text + font-level structure) |
| `pydantic` | Validate and type-check the AI JSON response |

---

## Setup

### 1. Prerequisites

- Python 3.11+
- A [Google Gemini API key](https://aistudio.google.com/apikey)

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your API key

```bash
# macOS / Linux
export GEMINI_API_KEY="AIza..."

# Windows (PowerShell)
$env:GEMINI_API_KEY = "AIza..."

# Windows (CMD)
set GEMINI_API_KEY=AIza...
```

> The tool also accepts `GOOGLE_API_KEY` as a fallback.

---

## Usage

### Web UI (Recommended)

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser. Upload a file, enter your API key, and click Analyse.

### CLI

```bash
# Analyse a single PDF
python main.py report.pdf

# Analyse a Word document
python main.py spec.docx

# Analyse multiple files at once
python main.py doc1.pdf doc2.docx --output-dir ./results

# Pass API key inline
python main.py report.pdf --api-key AIza...

# Skip AI analysis (metrics only, no API key required)
python main.py report.pdf --no-ai

# Print compact JSON to stdout
python main.py report.pdf --json-only
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--output-dir DIR` | `./output` | Directory for saved report files |
| `--api-key KEY` | env var | Gemini API key |
| `--no-ai` | off | Skip AI analysis (metrics only) |
| `--json-only` | off | Print JSON to stdout |

---

## Output

Two files are written per document into the output directory:

| File | Contents |
|------|----------|
| `<name>_report.json` | Full structured report (metrics + AI analysis) |
| `<name>_report.md` | Human-readable Markdown summary |

### Sample JSON Output

```json
{
  "generated_at": "2026-05-08T10:00:00Z",
  "document_metrics": {
    "file_name": "spec.pdf",
    "file_type": "pdf",
    "file_size_kb": 142.3,
    "page_count": 8,
    "is_page_count_estimated": false,
    "word_count": 3241,
    "char_count": 21450,
    "sentence_count": 128,
    "paragraph_count": 47,
    "heading_count": 12,
    "max_heading_depth": 2,
    "avg_words_per_paragraph": 28.5,
    "unique_words": 1985,
    "vocabulary_richness": 0.612,
    "table_count": 3,
    "image_count": 0,
    "code_block_count": 0,
    "url_count": 4,
    "estimated_reading_time_min": 16.2
  },
  "ai_analysis": {
    "readability_level": "Medium",
    "readability_score": 7,
    "content_clarity": "Content is generally clear with consistent terminology.",
    "structural_quality": "Well-Organized",
    "migration_readiness": "Needs Minor Cleanup",
    "migration_score": 7,
    "estimated_migration_effort": "Low",
    "strengths": [
      "Clear heading hierarchy",
      "Consistent tone and terminology"
    ],
    "issues": [
      "Some paragraphs exceed 150 words",
      "3 broken internal links"
    ],
    "suggestions": [
      "Break long paragraphs into bullet lists",
      "Validate all hyperlinks before migration"
    ],
    "summary": "The document is well-structured and mostly ready for migration. Minor cleanup of long paragraphs and broken links is recommended."
  }
}
```

---

## Metrics Extracted

| Metric | Description |
|--------|-------------|
| Page count | Exact (PDF) or estimated at ~300 words/page (DOCX) |
| Word count | Total whitespace-delimited words |
| Character count | Total characters including spaces |
| Sentence count | Approximate count via terminal punctuation |
| Paragraph count | Non-empty text blocks |
| Heading count | Style-based (DOCX) or font-size-detected (PDF) |
| Avg words/paragraph | Mean paragraph length |
| Vocabulary richness | Unique-word ratio (0 = repetitive, 1 = highly varied) |
| Tables / Images | Embedded object counts |
| Code blocks / URLs | Inline code fragments and hyperlink counts |
| Reading time | Estimated at 200 words per minute |

---

## AI Analysis Dimensions

| Dimension | Values |
|-----------|--------|
| Readability level | Easy / Medium / Complex |
| Readability score | 1-10 |
| Content clarity | Narrative assessment |
| Structural quality | Well-Organized / Moderately-Organized / Fragmented |
| Migration readiness | Ready / Needs Minor Cleanup / Requires Restructuring |
| Migration score | 1-10 |
| Estimated migration effort | Low / Medium / High |
| Strengths | List of positive attributes |
| Issues | List of problems found |
| Suggestions | Actionable improvements before migration |
| Summary | 2-3 sentence overall verdict |

---

## Project Structure

```
doc-migration-tool/
|-- app.py               # Flask web UI
|-- main.py              # CLI entry point
|-- requirements.txt     # Python dependencies
|-- README.md
|-- templates/
|   |-- index.html       # Web interface
|-- src/
    |-- __init__.py
    |-- parsers.py       # .docx and .pdf document parsing
    |-- metrics.py       # Structural & content metric extraction
    |-- ai_analyzer.py   # Google Gemini AI integration
    |-- reporter.py      # JSON + Markdown report generation
```
