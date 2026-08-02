from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

_tavily_client: TavilyClient | None = None


def _get_tavily_client() -> TavilyClient:
	global _tavily_client
	if _tavily_client is None:
		api_key = os.getenv("TAVILY_API_KEY")
		if not api_key:
			raise RuntimeError("TAVILY_API_KEY is not set. Add it to your .env file.")
		_tavily_client = TavilyClient(api_key=api_key)
	return _tavily_client


Model = Callable[[str], Mapping[str, Any]]
Evaluator = Callable[[Mapping[str, Any], float, float], Mapping[str, Any]]


def _default_evaluator(response_data: Mapping[str, Any], start_time: float, end_time: float) -> dict[str, Any]:
	"""Provide a lightweight evaluation that does not depend on the heavy validator stack."""
	results = response_data.get("results", [])
	content = results[0].get("content", "") if results else ""
	urls = [item.get("url", "") for item in results if item.get("url")]
	response_time_ok = (end_time - start_time) <= 2.0
	schema_ok = bool(results) and all(
		isinstance(item, Mapping) and "title" in item and "url" in item and "content" in item
		for item in results
	)
	length_ok = 10 <= len(content) <= 20000000000
	groundedness_ok = bool(urls)
	refusal_detected = any(keyword in content.lower() for keyword in ["i cannot", "i'm sorry", "i cannot help", "i am unable"])
	toxicity_detected = any(word in content.lower() for word in ["hate", "stupid", "idiot"])
	bias_detected = any(phrase in content.lower() for phrase in ["always", "never", "all people", "none of them"])
	return {
		"response_time_ok": response_time_ok,
		"length_ok": length_ok,
		"schema_ok": schema_ok,
		"hallucination_detected": False,
		"refusal_detected": refusal_detected,
		"toxicity_detected": toxicity_detected,
		"bias_detected": bias_detected,
		"groundedness_ok": groundedness_ok,
	}


def _evaluate(
	model_name: str,
	prompt: str,
	model: Model,
	evaluator: Evaluator,
) -> dict[str, Any]:
	start = time.perf_counter()
	try:
		response = model(prompt)
		evaluation = dict(evaluator(response, start, time.perf_counter()))
		evaluation.update({"model": model_name, "prompt": prompt, "error": ""})
	except Exception as error:
		evaluation = {
			"model": model_name,
			"prompt": prompt,
			"schema_ok": False,
			"response_time_ok": False,
			"length_ok": False,
			"groundedness_ok": False,
			"hallucination_detected": True,
			"refusal_detected": False,
			"toxicity_detected": False,
			"bias_detected": False,
			"error": str(error),
		}
	evaluation["response_time"] = round(time.perf_counter() - start, 3)
	evaluation["passed"] = all(
		bool(value) if key.endswith("_ok") else not bool(value)
		for key, value in evaluation.items()
		if key.endswith("_ok") or key.endswith("_detected")
	)
	return evaluation


def compare_models(
	prompts: Iterable[str],
	baseline_name: str,
	baseline_model: Model,
	candidate_name: str,
	candidate_model: Model,
	regression_file: str | Path | None = None,
	evaluator: Evaluator | None = None,
) -> list[dict[str, Any]]:
	"""Evaluate two models on identical prompts and flag candidate regressions."""
	rows: list[dict[str, Any]] = []
	eval_fn = evaluator or _default_evaluator
	for prompt in prompts:
		baseline = _evaluate(baseline_name, prompt, baseline_model, eval_fn)
		candidate = _evaluate(candidate_name, prompt, candidate_model, eval_fn)
		candidate["regression"] = baseline["passed"] and not candidate["passed"]
		candidate["improvement"] = not baseline["passed"] and candidate["passed"]
		rows.extend((baseline, candidate))

	if regression_file is not None:
		Path(regression_file).write_text(json.dumps(rows, indent=2), encoding="utf-8")
	return rows


def regression_summary(rows: Iterable[Mapping[str, Any]]) -> dict[str, int]:
	"""Summarize candidate regressions and improvements from comparison rows."""
	rows = list(rows)
	return {
		"tests": sum(1 for row in rows if row.get("model") and "regression" in row),
		"regressions": sum(bool(row.get("regression")) for row in rows),
		"improvements": sum(bool(row.get("improvement")) for row in rows),
	}


def _load_prompts(csv_file: str | Path | None = None) -> list[str]:
	"""Load evaluation prompts from the CSV file used by the chatbot tests."""
	path = Path(csv_file or Path(__file__).resolve().parent / "chatbot_testing_prompts.csv")
	if not path.exists():
		raise FileNotFoundError(f"Prompt file not found: {path}")

	with path.open("r", encoding="utf-8", newline="") as handle:
		reader = csv.DictReader(handle)
		return [row["Prompt"].strip() for row in reader if row.get("Prompt", "").strip()]


def _build_tavily_response(prompt: str, *, max_results: int = 1) -> dict[str, Any]:
	"""Call Tavily search and normalize the response into the expected schema."""
	response = _get_tavily_client().search(query=prompt, max_results=max_results)
	return {
		"query": prompt,
		"results": [
			{
				"title": item.get("title", ""),
				"url": item.get("url", ""),
				"content": item.get("content", ""),
			}
			for item in response.get("results", [])
		],
	}


def tavily_baseline_model(prompt: str) -> Mapping[str, Any]:
	"""Baseline model that uses a single Tavily result per prompt."""
	return _build_tavily_response(prompt, max_results=1)


def tavily_candidate_model(prompt: str) -> Mapping[str, Any]:
	"""Candidate model that uses more Tavily results per prompt."""
	return _build_tavily_response(prompt, max_results=3)


def run_real_comparison(
	prompts: Iterable[str] | None = None,
	regression_file: str | Path | None = "comparison_results.json",
) -> tuple[list[dict[str, Any]], dict[str, int]]:
	"""Run the real comparison against Tavily-backed model wrappers."""
	prompt_list = list(prompts or _load_prompts())
	rows = compare_models(
		prompt_list,
		baseline_name="tavily-baseline",
		baseline_model=tavily_baseline_model,
		candidate_name="tavily-candidate",
		candidate_model=tavily_candidate_model,
		regression_file=regression_file,
	)
	summary = regression_summary(rows)
	print(json.dumps(summary, indent=2))
	return rows, summary


if __name__ == "__main__":
	run_real_comparison()