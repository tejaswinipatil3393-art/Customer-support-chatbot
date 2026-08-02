from __future__ import annotations

from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Mapping

from jinja2 import Template


REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<title>{{ chatbot_name }} validation report</title>
	<style>
		body { font-family: Arial, sans-serif; margin: 32px; color: #1f2937; background: #f3f4f6; }
		h1, h2 { color: #12355b; }
		.card { background: #fff; padding: 20px; margin: 0 0 20px; border-radius: 8px; box-shadow: 0 2px 8px #0002; }
		.metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
		.metric { background: #eef4fb; padding: 14px; border-radius: 6px; }
		.metric strong { display: block; font-size: 1.4rem; margin-top: 4px; }
		table { width: 100%; border-collapse: collapse; }
		th { background: #12355b; color: white; text-align: left; }
		th, td { padding: 10px; border: 1px solid #d1d5db; vertical-align: top; }
		.pass { color: #147a46; font-weight: bold; }
		.fail { color: #b42318; font-weight: bold; }
		@media (max-width: 700px) { .metrics { grid-template-columns: repeat(2, 1fr); } body { margin: 16px; } }
	</style>
</head>
<body>
	<h1>{{ chatbot_name }} Validation Report</h1>
	<p>Generated {{ generated_at }} in {{ environment }}.</p>

	<div class="card">
		<h2>Summary</h2>
		<div class="metrics">
			<div class="metric">Total tests<strong>{{ total_tests }}</strong></div>
			<div class="metric">Passed<strong class="pass">{{ passed }}</strong></div>
			<div class="metric">Failed<strong class="fail">{{ failed }}</strong></div>
			<div class="metric">Pass rate<strong>{{ pass_rate }}%</strong></div>
		</div>
	</div>

	<div class="card">
		<h2>Test Results</h2>
		<table>
			<thead><tr><th>#</th><th>Prompt</th><th>Status</th><th>Checks</th><th>Response time</th></tr></thead>
			<tbody>
			{% for row in rows %}
				<tr>
					<td>{{ row.number }}</td>
					<td>{{ row.prompt }}</td>
					<td class="{{ 'pass' if row.passed else 'fail' }}">{{ 'PASS' if row.passed else 'FAIL' }}</td>
					<td>{{ row.checks }}</td>
					<td>{{ row.response_time }}</td>
				</tr>
			{% else %}
				<tr><td colspan="5">No test results were supplied.</td></tr>
			{% endfor %}
			</tbody>
		</table>
	</div>
</body>
</html>
"""

COMPARISON_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Model Comparison Report</title>
<style>
body { font-family: Arial, sans-serif; margin: 32px; color: #1f2937; background: #f3f4f6; }
.card { background: #fff; padding: 20px; margin-bottom: 20px; border-radius: 8px; }
table { width: 100%; border-collapse: collapse; } th, td { padding: 10px; border: 1px solid #d1d5db; text-align: left; }
th { background: #12355b; color: white; } .pass { color: #147a46; } .fail, .regression { color: #b42318; font-weight: bold; }
</style></head><body>
<h1>Model Comparison Report</h1>
<div class="card"><p>Tests: {{ tests }} | Regressions: {{ regressions }} | Improvements: {{ improvements }}</p></div>
<div class="card"><table><thead><tr><th>Prompt</th><th>Model</th><th>Status</th><th>Regression</th><th>Response time</th><th>Error</th></tr></thead>
<tbody>{% for row in rows %}<tr><td>{{ row.prompt }}</td><td>{{ row.model }}</td>
<td class="{{ 'pass' if row.passed else 'fail' }}">{{ 'PASS' if row.passed else 'FAIL' }}</td>
<td class="{{ 'regression' if row.regression else '' }}">{{ 'YES' if row.regression else 'NO' }}</td>
<td>{{ row.response_time }}</td><td>{{ row.error }}</td></tr>{% endfor %}</tbody>
</table></div></body></html>"""


class _ReportTextParser(HTMLParser):
	def __init__(self) -> None:
		super().__init__()
		self.parts: list[str] = []

	def handle_data(self, data: str) -> None:
		text = " ".join(data.split())
		if text:
			self.parts.append(text)


def _html_to_text(html: str) -> str:
	parser = _ReportTextParser()
	parser.feed(html)
	return "\n".join(parser.parts)


def generate_pdf(html: str, pdf_path: str | Path, base_dir: str | Path = ".") -> Path:
	"""Convert rendered HTML into a PDF file."""
	try:
		from weasyprint import HTML
	except (ImportError, OSError):
		HTML = None

	pdf_file = Path(pdf_path)
	pdf_file.parent.mkdir(parents=True, exist_ok=True)
	if HTML is not None:
		try:
			HTML(string=html, base_url=str(base_dir)).write_pdf(str(pdf_file))
			return pdf_file
		except OSError:
			pass

	try:
		from reportlab.lib.pagesizes import letter
		from reportlab.pdfgen.canvas import Canvas
	except ImportError as error:
		raise RuntimeError(
			"PDF generation requires WeasyPrint or ReportLab. Install with "
			"python -m pip install weasyprint reportlab."
		) from error

	canvas = Canvas(str(pdf_file), pagesize=letter)
	text = canvas.beginText(50, 750)
	text.setFont("Helvetica", 10)
	for line in _html_to_text(html).splitlines():
		text.textLine(line[:110])
		if text.getY() < 50:
			canvas.drawText(text)
			canvas.showPage()
			text = canvas.beginText(50, 750)
			text.setFont("Helvetica", 10)
	canvas.drawText(text)
	canvas.save()
	return pdf_file


def generate_report(
	results: Iterable[Mapping[str, Any]],
	output_dir: str | Path = ".",
	chatbot_name: str = "AI Customer Support Chatbot",
	environment: str = "local",
) -> tuple[Path, Path | None]:
	"""Generate an HTML report and, when available, a PDF beside it.

	Each result should contain a ``prompt`` key and boolean validator fields.
	The function returns ``(html_path, pdf_path)``; ``pdf_path`` is ``None``
	if PDF generation is unavailable.
	"""
	output_path = Path(output_dir)
	output_path.mkdir(parents=True, exist_ok=True)

	rows = []
	for number, result in enumerate(results, start=1):
		checks = {
			key: value
			for key, value in result.items()
			if key.endswith("_ok") or key.endswith("_detected")
		}
		passed = all(
			bool(value) if key.endswith("ok") else not bool(value)
			for key, value in checks.items()
		)
		rows.append({
			"number": number,
			"prompt": result.get("prompt", ""),
			"passed": passed,
			"checks": ", ".join(f"{key}={value}" for key, value in checks.items()),
			"response_time": result.get("response_time", "n/a"),
		})

	total_tests = len(rows)
	passed = sum(row["passed"] for row in rows)
	failed = total_tests - passed
	html = Template(REPORT_TEMPLATE).render(
		chatbot_name=chatbot_name,
		environment=environment,
		generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
		total_tests=total_tests,
		passed=passed,
		failed=failed,
		pass_rate=round((passed / total_tests) * 100, 1) if total_tests else 0,
		rows=rows,
	)

	html_path = output_path / "chatbot_validation_report.html"
	html_path.write_text(html, encoding="utf-8")

	pdf_path = output_path / "chatbot_validation_report.pdf"
	try:
		generate_pdf(html, pdf_path, output_path)
	except (ImportError, OSError, RuntimeError):
		pdf_path = None

	return html_path, pdf_path


def generate_comparison_report(
	rows: Iterable[Mapping[str, Any]],
	output_dir: str | Path = ".",
) -> tuple[Path, Path | None]:
	"""Generate HTML/PDF output for two-model comparison results."""
	rows = list(rows)
	regressions = sum(bool(row.get("regression")) for row in rows)
	improvements = sum(bool(row.get("improvement")) for row in rows)
	html = Template(COMPARISON_TEMPLATE).render(
		rows=rows,
		tests=sum("regression" in row for row in rows),
		regressions=regressions,
		improvements=improvements,
	)
	output_path = Path(output_dir)
	output_path.mkdir(parents=True, exist_ok=True)
	html_path = output_path / "model_comparison_report.html"
	html_path.write_text(html, encoding="utf-8")
	pdf_path = output_path / "model_comparison_report.pdf"
	try:
		generate_pdf(html, pdf_path, output_path)
	except (ImportError, OSError, RuntimeError):
		pdf_path = None
	return html_path, pdf_path


if __name__ == "__main__":
	html_file, pdf_file = generate_report([])
	print(f"HTML report generated: {html_file}")
	if pdf_file:
		print(f"PDF report generated: {pdf_file}")
	else:
		print("PDF generation skipped; install WeasyPrint to enable it.")
