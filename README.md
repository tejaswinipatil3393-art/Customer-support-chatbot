# AI Customer Support Chatbot Validation

This repository contains a small validation framework for chatbot responses using Tavily search results, response schema checks, and report generation.

## Overview

- `Validators.py`: main validation runner that reads prompts from `chatbot_testing_prompts.csv`, queries Tavily, evaluates responses, and generates HTML/PDF reports.
- `read_csv.py`: helper function for reading a CSV and searching rows by keyword.
- `model_comparison.py`: utilities to compare two model results across prompt sets and detect regressions/improvements.
- `reports.py`: renders HTML validation/comparison reports and optionally generates PDF output.
- `data_loader.py`: Tavily client wrapper and evaluation helpers used by comparison logic.
- `__ini__.py`: package entrypoint for model schema imports.

## Requirements

Install dependencies from `requirements.txt`:

```powershell
python -m pip install -r requirements.txt
```

## Setup

1. Create a virtual environment in the project root if needed:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

2. Add your Tavily API key to a `.env` file in the project root:

```text
TAVILY_API_KEY=your_api_key_here
```

## Usage

Run the primary validation script:

```powershell
python Validators.py
```

This will:
- load prompts from `chatbot_testing_prompts.csv`
- query Tavily for each prompt
- evaluate response schema, length, groundedness, toxicity, bias, and response time
- save `chatbot_validation_report.html`
- save `chatbot_validation_report.pdf` if PDF support is available

Run the model comparison helper:

```powershell
python model_comparison.py
```

## Testing

This project includes a `pytest.ini` configuration. Add tests under the repository root with names matching `test_*.py` or `*_test.py`.

Run tests with:

```powershell
pytest
```

## Notes

- The project currently relies on Tavily via the `tavily-python` package.
- PDF generation is supported through `weasyprint` and falls back to `reportlab` when needed.
- If you extend the project, keep third-party dependencies updated in `requirements.txt`.
