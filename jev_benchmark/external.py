"""Reproducible external evaluation of native System One decision models."""

from hashlib import sha256
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import random
import statistics
import sys
from time import perf_counter, sleep
from urllib.parse import urlsplit

import httpx

from . import ENV_PATH, ModelError, rounded_probability_bounds, valid_probability_sum
from .intranet import is_safe_base_url
from .jev_api import JevClient, read_config
from .microsoft import MicrosoftClient

TARGET_MODEL = "qwen35-4b-jev-v1"
MODEL_KEYS = ("jev", "microsoft", "intranet")


def digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    return sha256(encoded).hexdigest()


class NativeClient:
    def __init__(
        self, transport: httpx.BaseTransport | None = None, *, model_key: str = "intranet",
        env_path: Path = ENV_PATH, fresh_connections: bool = False,
    ) -> None:
        self.model_key = model_key
        if model_key in ("jev", "microsoft"):
            adapter = JevClient(env_path) if model_key == "jev" else MicrosoftClient(env_path)
            self._endpoint, api_key, self.model = adapter._endpoint, adapter._key, adapter.model
            self.accepts_model = adapter.accepts_model
        elif model_key == "intranet":
            config = read_config(("INTRANET_BASE_URL", "INTRANET_API_KEY", "INTRANET_MODEL"), env_path)
            base_url = config["INTRANET_BASE_URL"]
            if config["INTRANET_MODEL"] != TARGET_MODEL:
                raise ModelError(f"External evaluation requires INTRANET_MODEL={TARGET_MODEL}.")
            if not is_safe_base_url(base_url) or urlsplit(base_url).hostname == "api.typesafe.ai":
                raise ModelError("External evaluation requires the configured self-hosted endpoint.")
            if not config["INTRANET_API_KEY"]:
                raise ModelError("Missing INTRANET_API_KEY.")
            self._endpoint = base_url.rstrip("/") + "/v1/systemone"
            api_key, self.model = config["INTRANET_API_KEY"], TARGET_MODEL
            self.accepts_model = lambda actual: actual == TARGET_MODEL
        else:
            raise ValueError(f"Unknown model key: {model_key}.")
        self.http_keepalive = not fresh_connections
        connection_options = {"limits": httpx.Limits(max_keepalive_connections=0)} if fresh_connections else {}
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120.0, follow_redirects=False, transport=transport,
            **connection_options,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._client.close()

    def request(self, state: object, questions: dict) -> dict:
        payload = {"model": self.model, "state": state, "questions": questions}
        receipt = {"request_sha256": digest(payload)}
        start = perf_counter()
        try:
            response = self._client.post(self._endpoint, json=payload)
            receipt["http_status"] = response.status_code
            if response.status_code == 200:
                receipt["response_sha256"] = sha256(response.content).hexdigest()
                try:
                    receipt["response"] = response.json()
                except ValueError:
                    receipt["error"] = "invalid_json"
            else:
                receipt["error"] = f"http_{response.status_code}"
        except httpx.TimeoutException:
            receipt["error"] = "timeout_no_retry"
        except httpx.RequestError as error:
            receipt["error"] = "connection_error_no_retry"
            receipt["error_type"] = type(error).__name__
        receipt["seconds"] = perf_counter() - start
        return receipt


def rounded_score_interval(bounds: tuple[list[float], list[float]]) -> tuple[float, float]:
    lower, upper = bounds
    result = []
    for indices in (range(len(lower)), range(len(lower) - 1, -1, -1)):
        remaining = max(0.0, 1 - sum(lower))
        score = sum(index * value for index, value in enumerate(lower))
        for index in indices:
            added = min(remaining, upper[index] - lower[index])
            score += index * added
            remaining -= added
        result.append(score)
    return result[0], result[1]


def distribution(item: dict, receipt: dict, model: str = TARGET_MODEL) -> list[float]:
    response = receipt.get("response")
    if not isinstance(response, dict) or response.get("model") != model:
        raise ValueError("missing_or_wrong_model")
    answer = response.get("answers", {}).get("decision")
    kind = item["question"]["type"]
    if not isinstance(answer, dict) or answer.get("type") != kind:
        raise ValueError("missing_or_wrong_answer_type")
    labels = item["labels"]
    if kind == "noul":
        value = answer.get("noul")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("invalid_noul")
        probabilities = [1 - value, value]
    else:
        values = answer.get("probabilities")
        if not isinstance(values, dict) or set(values) != set(labels):
            raise ValueError("invalid_probability_keys")
        probabilities = [values[label] for label in labels]
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) or not 0 <= value <= 1 for value in probabilities):
        raise ValueError("invalid_probability_value")
    if not valid_probability_sum(probabilities, model):
        raise ValueError("invalid_probability_sum")
    if kind == "choice":
        selected = answer.get("choice")
        if selected not in labels or probabilities[labels.index(selected)] < max(probabilities) - 1e-8:
            raise ValueError("invalid_choice")
    if kind == "score":
        score = answer.get("score")
        expected = sum(index * value for index, value in enumerate(probabilities))
        if (isinstance(score, bool) or not isinstance(score, (int, float))
                or not math.isfinite(score) or not 0 <= score <= len(labels) - 1):
            raise ValueError("invalid_score")
        if not math.isclose(score, expected, abs_tol=1e-5):
            bounds = rounded_probability_bounds(probabilities, model)
            if bounds is None or not math.isclose(score * 100, round(score * 100), abs_tol=1e-8, rel_tol=0):
                raise ValueError("invalid_score")
            low, high = rounded_score_interval(bounds)
            if not low - 0.005 - 1e-12 <= score <= high + 0.005 + 1e-12:
                raise ValueError("invalid_score")
    return probabilities


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def latency_statistics(values: list[float]) -> dict:
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("Latency samples must be finite nonnegative numbers.")
    return {
        "n": len(values), "mean_seconds": statistics.mean(values) if values else None,
        **{f"p{int(quantile * 100)}_seconds": percentile(values, quantile)
           for quantile in (0.5, 0.9, 0.95, 0.99)},
        "sum_request_seconds": sum(values),
        "scope": "valid_successful_responses_only",
        "percentile_method": "linear interpolation at (n-1)*quantile",
    }


def ranks(values: list[float]) -> list[float]:
    positions = {}
    for index, value in enumerate(sorted(values)):
        positions.setdefault(value, []).append(index)
    return [statistics.mean(positions[value]) for value in values]


def cluster_interval(rows: list[dict]) -> list[float] | None:
    scored = [row for row in rows if row.get("gold") is not None]
    if not scored:
        return None
    groups = {}
    for row in scored:
        groups.setdefault(row.get("group", row["id"]), []).append(int(row["correct"]))
    clusters = list(groups.values())
    rng = random.Random(20261002)
    samples = []
    for _ in range(1000):
        draw = [rng.choice(clusters) for _ in clusters]
        samples.append(sum(sum(group) for group in draw) / sum(len(group) for group in draw))
    return [percentile(samples, 0.025), percentile(samples, 0.975)]


def metrics(rows: list[dict]) -> dict:
    valid = [row for row in rows if row.get("valid")]
    labeled = [row for row in rows if row.get("gold") is not None]
    calibrated = [row for row in valid if row.get("gold") is not None]
    numeric = [row for row in valid if row.get("target_score") is not None]
    errors = {}
    for row in rows:
        if not row.get("valid"):
            reason = row.get("error", "unattempted")
            errors[reason] = errors.get(reason, 0) + 1
    result = {
        "n": len(rows), "attempted": sum(row.get("attempted", False) for row in rows),
        "valid": len(valid), "errors": errors,
        "accuracy": sum(row["correct"] for row in labeled) / len(labeled) if labeled else None,
        "accuracy_ci95_cluster_bootstrap": cluster_interval(rows),
        "probability_metric_n": len(calibrated),
        "reported_probability_sum_deviation_n": sum(
            not math.isclose(sum(row["probabilities"]), 1.0, abs_tol=0.001, rel_tol=0) for row in valid
        ),
        "maximum_reported_probability_sum_error": max(
            (abs(sum(row["probabilities"]) - 1.0) for row in valid), default=0.0,
        ),
    }
    result["success_latency"] = latency_statistics([row["seconds"] for row in valid])
    for key in ("mean_seconds", "p50_seconds", "p90_seconds", "p95_seconds", "p99_seconds"):
        result[key] = result["success_latency"][key]
    result["status"] = (
        "complete" if len(valid) == len(rows) and rows else
        "unattempted" if result["attempted"] == 0 else
        "failed" if result["attempted"] == len(rows) else "incomplete"
    )
    result["execution_complete"] = bool(rows) and result["attempted"] == len(rows)
    if calibrated:
        result["brier_sum"] = statistics.mean(
            sum((predicted - gold) ** 2 for predicted, gold in zip(row["probabilities"], row["gold"]))
            for row in calibrated
        )
        result["nll_epsilon_1e-15"] = statistics.mean(
            -sum(gold * math.log(max(predicted, 1e-15))
                 for predicted, gold in zip(row["probabilities"], row["gold"]))
            for row in calibrated
        )
        result["zero_mass_gold_rows"] = sum(
            any(gold > 0 and predicted == 0 for predicted, gold in zip(row["probabilities"], row["gold"]))
            for row in calibrated
        )
        bins = []
        for index in range(10):
            selected = [row for row in calibrated if min(int(max(row["probabilities"]) * 10), 9) == index]
            if selected:
                bins.append({"bin": index, "n": len(selected),
                             "p_max": statistics.mean(max(row["probabilities"]) for row in selected),
                             "soft_correctness": statistics.mean(row["gold"][row["selected_index"]] for row in selected)})
        result["ece_10_equal_width"] = sum(
            entry["n"] * abs(entry["p_max"] - entry["soft_correctness"]) for entry in bins
        ) / len(calibrated)
        result["calibration_bins"] = bins
        risk = []
        for threshold in (0.5, 0.7, 0.8, 0.9, 0.95, 0.99):
            accepted = [row for row in calibrated if max(row["probabilities"]) >= threshold]
            risk.append({"threshold_p_max": threshold, "n": len(accepted),
                         "coverage": len(accepted) / len(rows),
                         "error_rate": 1 - sum(row["correct"] for row in accepted) / len(accepted) if accepted else None})
        result["risk_coverage_descriptive"] = risk
    if labeled and len({tuple(row["labels"]) for row in labeled}) == 1:
        scores = []
        for label in range(len(labeled[0]["labels"])):
            positives = sum(row["gold_index"] == label for row in labeled)
            predicted = sum(row.get("selected_index") == label for row in labeled)
            true_positives = sum(row["gold_index"] == label and row.get("selected_index") == label for row in labeled)
            if positives or predicted:
                scores.append(2 * true_positives / (positives + predicted))
        result["macro_f1_present_labels"] = statistics.mean(scores) if scores else None
    if numeric:
        target = [row["target_score"] for row in numeric]
        prediction = [row["expected_score"] for row in numeric]
        result["ordinal_n"] = len(numeric)
        result["ordinal_mae"] = statistics.mean(abs(left - right) for left, right in zip(target, prediction))
        try:
            result["spearman"] = statistics.correlation(ranks(target), ranks(prediction))
        except statistics.StatisticsError:
            result["spearman"] = None
    return result


def summarize_external(
    manifest: dict, receipts: list[dict], model: str = TARGET_MODEL, *, actual_model: str | None = None,
) -> dict:
    by_id = {receipt["id"]: receipt for receipt in receipts}
    if len(by_id) != len(receipts) or set(by_id) - {item["id"] for item in manifest["items"]}:
        raise ValueError("Duplicate or unknown response IDs.")
    rows = []
    for item in manifest["items"]:
        receipt = by_id.get(item["id"])
        row = {**item, "valid": False, "correct": False, "attempted": receipt is not None}
        if receipt:
            request_hash = digest({"model": model, "state": item["state"], "questions": {"decision": item["question"]}})
            if receipt.get("request_sha256", request_hash) != request_hash:
                raise ValueError("Saved response does not match the frozen request.")
            row["seconds"] = receipt["seconds"]
            try:
                if receipt.get("error"):
                    raise ValueError(receipt["error"])
                probabilities = distribution(item, receipt, actual_model or model)
                selected = max(range(len(probabilities)), key=probabilities.__getitem__)
                if item["question"]["type"] == "choice":
                    selected = item["labels"].index(receipt["response"]["answers"]["decision"]["choice"])
                expected_score = sum(index * value for index, value in enumerate(probabilities))
                if item["question"]["type"] == "score":
                    expected_score = receipt["response"]["answers"]["decision"]["score"]
                row.update(valid=True, probabilities=probabilities, selected_index=selected,
                           correct=selected == item.get("gold_index"),
                           expected_score=expected_score)
            except (ValueError, TypeError, AttributeError, KeyError) as error:
                row["error"] = str(error) if isinstance(error, ValueError) else "invalid_response"
        rows.append(row)
    primary = [row for row in rows if not row.get("permutation_of")]
    suites = {suite: metrics([row for row in primary if row["suite"] == suite])
              for suite in sorted({row["suite"] for row in primary})}
    primitives = {kind: metrics([row for row in primary if row["question"]["type"] == kind])
                  for kind in ("choice", "noul", "score")}
    pairs = []
    originals = {row["id"]: row for row in primary}
    for row in rows:
        if row.get("permutation_of"):
            original = originals[row["permutation_of"]]
            if row["valid"] and original["valid"]:
                left = original["labels"][original["selected_index"]]
                right = row["labels"][row["selected_index"]]
                pairs.append({"suite": row["suite"], "same_choice": left == right,
                              "both_correct": row["correct"] and original["correct"]})
    consistency = {}
    for suite in sorted({row["suite"] for row in rows if row.get("permutation_of")}):
        selected = [pair for pair in pairs if pair["suite"] == suite]
        total = sum(row["suite"] == suite and bool(row.get("permutation_of")) for row in rows)
        consistency[suite] = {
            "total_pairs": total, "valid_pairs": len(selected),
            "same_choice_rate": sum(row["same_choice"] for row in selected) / total,
            "both_correct_rate": sum(row["both_correct"] for row in selected) / total,
        }
    success_latency = latency_statistics([row["seconds"] for row in rows if row["valid"]])
    families = {family: metrics([row for row in primary if row.get("family") == family and row["suite"] == "jevbench-hard"])
                for family in sorted({row["family"] for row in primary if row["suite"] == "jevbench-hard"})}
    responses = [receipt["response"] for receipt in receipts if isinstance(receipt.get("response"), dict)]
    usage = [response["usage"] for response in responses if isinstance(response.get("usage"), dict)]
    def token_total(key):
        values = [entry.get(key) for entry in usage]
        if len(values) != len(receipts) or any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values):
            return None
        return sum(values)
    return {"suites": suites, "primitives": primitives, "option_reversal": consistency,
            "total_requests": len(rows), "recorded_requests": len(receipts),
            "logical_items": len(rows), "recorded_items": len(receipts), "physical_requests": len(receipts),
            "manifest_sha256": digest(manifest), "model": actual_model or model, "requested_model": model,
            "primary_decisions": len(primary), "hard_families": families,
            "probability_reporting": (
                "Jev 1.13 hundredths: feasible rounding bounds, native Score retained, no normalization"
                if (actual_model or model) == "jev-1.13.0" else "native reported values; no normalization"
            ),
            "dataset_sources": manifest.get("sources", []), "protocol": manifest.get("protocol", {}),
            "systems": {"actual_models": sorted({response["model"] for response in responses if isinstance(response.get("model"), str)}),
                        "valid_responses": sum(row["valid"] for row in rows),
                        "success_latency": success_latency,
                        **{key: success_latency[key] for key in (
                            "mean_seconds", "p50_seconds", "p90_seconds", "p95_seconds",
                            "p99_seconds", "sum_request_seconds",
                        )},
                        "reported_input_tokens": token_total("input_tokens"),
                        "reported_output_tokens": token_total("output_tokens"),
                        "cost_usd": None, "cost_basis": (
                            "self-hosted; GPU cost and power were not measured" if model == TARGET_MODEL
                            else "hosted API; billed cost was not measured"
                        )}}


def write_report(summary: dict, path: Path) -> None:
    def display(value):
        return "N/A" if value is None else f"{value:.4f}"

    lines = [f"# {summary['model']} External Evaluation", "",
             f"Model: `{summary['model']}`. Manifest SHA-256: `{summary['manifest_sha256']}`.", "",
             f"Requested model: `{summary.get('requested_model', summary['model'])}`. "
             f"Run ended UTC: {summary.get('completed_at', 'not recorded')}.", "",
             f"Logical items recorded: {summary['recorded_requests']}/{summary['total_requests']}. "
             f"Physical HTTP attempts: {summary.get('physical_requests', summary['recorded_requests'])}.", "",
             f"**Run status: {summary.get('status', 'complete' if summary['systems']['valid_responses'] == summary['total_requests'] else 'failed')}**. "
             f"Valid responses: {summary['systems']['valid_responses']}/{summary['total_requests']}.", "",
             f"All configured items attempted: {summary['recorded_requests'] == summary['total_requests']}. "
             f"Minimum request-start interval: {summary.get('minimum_request_interval_seconds', 0)} seconds "
             "(excluded from measured request latency).", "",
             f"Network error policy: `{summary.get('network_error_policy', 'not recorded')}`. "
             f"Keepalive for this segment's new requests: {summary.get('new_requests_http_keepalive', 'not recorded')}. "
             "Retained responses keep their original transport conditions.", "",
             f"Probability reporting: {summary.get('probability_reporting', 'not recorded')}. "
             "Jev hundredths are not renormalized; rounded zero probabilities can inflate floored NLL, "
             "and its native reported Score is retained for MAE and Spearman.", "",
             "Incomplete or unattempted tasks are not assigned benchmark scores in this report. "
             "Fully attempted tasks count API failures as incorrect; probability metrics use valid responses only. "
             "The JSON retains strict planned-denominator accuracy for auditing failures.", "",
             "Latency statistics include only valid successful responses, including incorrect predictions. "
             "HTTP failures, timeouts, invalid responses, request-spacing sleeps and outage waits are excluded.", "",
             "| Suite | N | Attempted | Valid | Status | Accuracy | Brier (sum) | NLL | ECE | MAE | Spearman | p50 / p90 / p95 / p99 (s) |",
             "| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for suite, values in summary["suites"].items():
        complete = values.get("attempted", values["valid"]) == values["n"]
        score = lambda key: display(values.get(key)) if complete else "N/A"
        status = values.get("status", "complete" if complete else "incomplete")
        lines.append(f"| {suite} | {values['n']} | {values['attempted']} | {values['valid']} | {status} | "
                     f"{score('accuracy')} | {score('brier_sum')} | {score('nll_epsilon_1e-15')} | "
                     f"{score('ece_10_equal_width')} | {score('ordinal_mae')} | {score('spearman')} | "
                     f"{display(values['p50_seconds'])} / {display(values.get('p90_seconds'))} / "
                     f"{display(values['p95_seconds'])} / {display(values.get('p99_seconds'))} |")
    if summary.get("continuation"):
        continued = summary["continuation"]
        lines += ["", "## Explicit continuation", "",
                  f"Retained {continued['retained_requests']} original attempts, including "
                  f"{continued['retained_errors']} errors, from `{continued['source_directory']}`. "
                  f"Sent {continued['new_requests']} previously unattempted items; no saved attempt was resent.",
                  f"Continuation started UTC: {continued['started_at']}."]
    if summary.get("user_directed_repair"):
        repaired = summary["user_directed_repair"]
        lines += ["", "## User-directed missing-answer recovery", "",
                  f"Original valid answers: {repaired['initial_valid_items']}. "
                  f"Explicit additional attempts: {repaired['new_physical_requests']}. "
                  "Only items lacking valid responses were sent again; valid wrong predictions were not repeated.",
                  f"Source snapshot: `{repaired['source_directory']}`. "
                  "Original responses and the complete physical attempt history remain local and unchanged.",
                  f"First-pass failed attempts retained: {summary['failed_physical_requests']}."]
    lines += ["", "## Interpretation", "",
              "- JevBench results cover only the pinned, published public cohorts, not the full leaderboard.",
              "- Accuracy counts failures and unattempted items as incorrect; probability metrics use valid vectors only.",
              "- Brier uses the multiclass sum convention. NLL floors probabilities at 1e-15 and reports zero-mass rows.",
              "- ECE uses top-label probability and reference agreement, not the model's entropy-based confidence.",
              "- Score tasks retain expected-level MAE and Spearman; continuous STS-B targets have no fabricated gold distribution.",
              "- Risk/coverage curves are descriptive; no threshold or temperature is fitted on these test cases.",
              "- Accuracy intervals resample whole scenario groups (1,000 bootstrap draws).",
              "- Latency is serial HTTP client wall time, not normalized GPU throughput.",
              "- No model tuning, retry, hidden probability normalization, or response-token scoring.",
              "- Hosted API calls may be billed; no price or cost is inferred from token counts.",
              "- Zero-shot means no benchmark-directed tuning in this run; pretraining and historical training overlap are not ruled out.",
              "- Actual model identity was checked on every response; deployed weight hashes were not independently inspected.",
              "", "## Failures", ""]
    if all(not values["errors"] for values in summary["suites"].values()):
        lines.append("No failed or invalid primary responses.")
    for suite, values in summary["suites"].items():
        if values["errors"]:
            lines.append(f"- {suite}: `{json.dumps(values['errors'], sort_keys=True)}`")
    lines += ["", "## Option Reversal", "",
              "| Suite | Valid pairs | Same choice | Both correct |", "| --- | ---: | ---: | ---: |"]
    for suite, values in summary["option_reversal"].items():
        complete = values["valid_pairs"] == values.get("total_pairs", values["valid_pairs"])
        lines.append(f"| {suite} | {values['valid_pairs']}/{values.get('total_pairs', values['valid_pairs'])} | "
                     f"{display(values['same_choice_rate']) if complete else 'N/A'} | "
                     f"{display(values['both_correct_rate']) if complete else 'N/A'} |")
    lines += ["", "## High-Probability Decisions", "",
              "Descriptive p_max >= 0.9 slice; these are not fitted deployment thresholds. "
              "Incomplete-task slices are diagnostics only, not completed benchmark results.", "",
              "| Suite | Valid / N | Status | Accepted | Coverage | Error rate |",
              "| --- | ---: | --- | ---: | ---: | ---: |"]
    for suite, values in summary["suites"].items():
        selected = next((entry for entry in values.get("risk_coverage_descriptive", []) if entry["threshold_p_max"] == 0.9), None)
        if selected:
            status = values.get("status", "complete" if values["valid"] == values["n"] else "incomplete")
            lines.append(f"| {suite} | {values['valid']}/{values['n']} | {status} | {selected['n']} | "
                         f"{selected['coverage']:.4f} | {display(selected['error_rate'])} |")
    lines += ["", "## Systems", "", f"```json\n{json.dumps(summary['systems'], indent=2)}\n```", "",
              "## Data Revisions", "",
              "| Repository | Revision | File | Source license |", "| --- | --- | --- | --- |"]
    for source in summary["dataset_sources"]:
        lines.append(f"| {source['repo']} | {source['revision']} | {source['file']} | {source['license']} |")
    lines += ["", "Raw source text and responses remain local and gitignored; upstream licenses still apply.",
              "Unspecified source licenses are not treated as permission to redistribute."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_continuation(manifest: dict, source: Path, model_key: str) -> tuple[list[dict], dict]:
    saved = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    previous = json.loads((source / "summary.json").read_text(encoding="utf-8"))
    if digest(saved) != digest(manifest) or previous.get("model_key", "intranet") != model_key:
        raise ValueError("Continuation requires the same frozen manifest and model key.")
    receipts = [json.loads(line) for line in (source / "responses.jsonl").read_text(encoding="utf-8").splitlines()]
    items = manifest["items"]
    if not receipts or len(receipts) >= len(items):
        raise ValueError("Continuation requires a nonempty, incomplete run.")
    if [receipt["id"] for receipt in receipts] != [item["id"] for item in items[:len(receipts)]]:
        raise ValueError("Saved responses must be an exact manifest prefix; no attempted item may be resent.")
    if len(list((source / "attempts").glob("*.json"))) != len(receipts):
        raise ValueError("A saved attempt lacks a response; continuation cannot safely infer whether it was sent.")
    requested = previous.get("requested_model", TARGET_MODEL)
    for index, (item, receipt) in enumerate(zip(items, receipts)):
        expected = digest({"model": requested, "state": item["state"], "questions": {"decision": item["question"]}})
        marker = json.loads((source / "attempts" / f"{index:05d}.json").read_text(encoding="utf-8"))
        if (
            marker.get("id") != item["id"] or marker.get("request_sha256") != expected
            or receipt.get("request_sha256") != expected
        ):
            raise ValueError("Continuation request integrity check failed.")
    recomputed = summarize_external(manifest, receipts, requested, actual_model=previous["model"])
    if (
        previous["manifest_sha256"] != digest(manifest) or previous["recorded_requests"] != len(receipts)
        or previous["systems"]["valid_responses"] != recomputed["systems"]["valid_responses"]
    ):
        raise ValueError("Continuation summary differs from its saved responses.")
    return receipts, previous


def run_external(
    manifest: dict, output: Path, client=None, *, model_key: str = "intranet",
    continue_from: Path | None = None, min_interval: float = 0.0,
    continue_on_network_errors: bool = False, fresh_connections: bool = False,
) -> dict:
    items = manifest["items"]
    if not items or len({item["id"] for item in items}) != len(items):
        raise ValueError("Manifest requires nonempty, unique item IDs.")
    if output.exists():
        raise FileExistsError(output)
    if not math.isfinite(min_interval) or min_interval < 0:
        raise ValueError("Minimum request interval must be finite and nonnegative.")
    receipts, previous = load_continuation(manifest, continue_from, model_key) if continue_from else ([], None)
    native = client or NativeClient(model_key=model_key, fresh_connections=fresh_connections)
    requested_model = native.model
    actual_model = previous["model"] if previous and previous["systems"]["actual_models"] else None
    initial_count = len(receipts)
    continued_at = datetime.now(timezone.utc).isoformat()
    with native as active:
        if previous and (
            requested_model != previous.get("requested_model", TARGET_MODEL)
            or (actual_model is not None and not native.accepts_model(actual_model))
        ):
            raise ValueError("Continuation configured model differs from the original run.")
        output.mkdir(parents=True, exist_ok=False)
        (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        attempts = output / "attempts"
        attempts.mkdir()
        if continue_from:
            for index in range(initial_count):
                filename = f"{index:05d}.json"
                (attempts / filename).write_bytes((continue_from / "attempts" / filename).read_bytes())
        with (output / "responses.jsonl").open("x", encoding="utf-8") as log:
            for receipt in receipts:
                log.write(json.dumps(receipt, ensure_ascii=False, allow_nan=False) + "\n")
            log.flush()
            last_start = None
            consecutive_network_errors = 0
            for index, item in enumerate(items[initial_count:], start=initial_count):
                if last_start is not None and min_interval:
                    delay = min_interval - (perf_counter() - last_start)
                    if delay > 0:
                        sleep(delay)
                last_start = perf_counter()
                payload = {"model": requested_model, "state": item["state"], "questions": {"decision": item["question"]}}
                with (attempts / f"{index:05d}.json").open("x", encoding="utf-8") as marker:
                    json.dump({"id": item["id"], "request_sha256": digest(payload),
                               "started_at": datetime.now(timezone.utc).isoformat()}, marker)
                receipt = {"id": item["id"], **active.request(item["state"], {"decision": item["question"]})}
                log.write(json.dumps(receipt, ensure_ascii=False, allow_nan=False) + "\n")
                log.flush()
                receipts.append(receipt)
                if receipt.get("error"):
                    if continue_on_network_errors and receipt["error"] in (
                        "connection_error_no_retry", "timeout_no_retry",
                    ):
                        consecutive_network_errors += 1
                        if consecutive_network_errors < 3:
                            print(f"Recorded error at {index + 1}/{len(items)}; "
                                  "moving to the NEXT unattempted item without retry.", flush=True)
                            sleep(5.0)
                            continue
                    print(f"Stopped at {index + 1}/{len(items)}: {receipt['error']}", flush=True)
                    break
                response = receipt.get("response")
                if isinstance(response, dict):
                    returned_model = response.get("model")
                    accepted = native.accepts_model(returned_model)
                    if not accepted or (actual_model is not None and returned_model != actual_model):
                        print("Stopped: actual model mismatch.", flush=True)
                        break
                    actual_model = returned_model
                try:
                    distribution(item, receipt, actual_model or requested_model)
                except (ValueError, TypeError, AttributeError, KeyError):
                    print(f"Stopped at {index + 1}/{len(items)}: invalid native response.", flush=True)
                    break
                consecutive_network_errors = 0
                if (index + 1) % 25 == 0 or index + 1 == len(items):
                    print(f"Recorded {index + 1}/{len(items)}", flush=True)
    summary = summarize_external(manifest, receipts, requested_model, actual_model=actual_model)
    summary["model_key"] = model_key
    summary["status"] = (
        "complete" if len(receipts) == len(items) and summary["systems"]["valid_responses"] == len(items)
        else "failed"
    )
    summary["completed_at"] = datetime.now(timezone.utc).isoformat()
    summary["minimum_request_interval_seconds"] = min_interval
    summary["new_requests_http_keepalive"] = native.http_keepalive if isinstance(native, NativeClient) else None
    summary["network_error_policy"] = (
        "record_and_continue_next_item; stop_after_3_consecutive; never_retry"
        if continue_on_network_errors else "stop_without_retry"
    )
    summary["execution_complete"] = len(receipts) == len(items)
    if previous:
        summary["continuation"] = {
            "source_directory": continue_from.name, "retained_requests": initial_count,
            "retained_errors": sum(bool(receipt.get("error")) for receipt in receipts[:initial_count]),
            "new_requests": len(receipts) - initial_count, "started_at": continued_at,
            "previous_completed_at": previous["completed_at"],
        }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    write_report(summary, output / "report.md")
    return summary


def repair_invalid_items(
    manifest: dict, source: Path, output: Path, client=None, *, model_key: str,
    min_interval: float = 1.25,
) -> dict:
    """Explicitly recover only missing valid answers, retaining every physical attempt."""
    if output.exists():
        raise FileExistsError(output)
    if not math.isfinite(min_interval) or min_interval < 0:
        raise ValueError("Minimum request interval must be finite and nonnegative.")
    saved = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    previous = json.loads((source / "summary.json").read_text(encoding="utf-8"))
    if digest(saved) != digest(manifest) or previous.get("model_key", "intranet") != model_key:
        raise ValueError("Recovery requires the same frozen manifest and model key.")
    requested, actual = previous.get("requested_model", TARGET_MODEL), previous["model"]
    receipts = [json.loads(line) for line in (source / "responses.jsonl").read_text(encoding="utf-8").splitlines()]
    history_path = source / "attempt-history.jsonl"
    history = ([json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines()]
               if history_path.exists() else list(receipts))
    items = {item["id"]: item for item in manifest["items"]}
    by_id = {receipt["id"]: receipt for receipt in receipts}
    if len(by_id) != len(receipts) or set(by_id) != set(items):
        raise ValueError("Recovery requires a complete logical item ledger; use continuation for unattempted items.")
    history_by_id = {}
    for receipt in history:
        if receipt["id"] not in items:
            raise ValueError("Unknown physical attempt ID.")
        item = items[receipt["id"]]
        expected = digest({"model": requested, "state": item["state"], "questions": {"decision": item["question"]}})
        if receipt.get("request_sha256") != expected:
            raise ValueError("Recovery request integrity check failed.")
        history_by_id.setdefault(receipt["id"], []).append(receipt)
    for identifier, receipt in by_id.items():
        attempts = history_by_id.get(identifier, [])
        valid = []
        for attempt in attempts:
            try:
                if attempt.get("error"):
                    raise ValueError(attempt["error"])
                distribution(items[identifier], attempt, actual)
            except (ValueError, TypeError, AttributeError, KeyError):
                continue
            valid.append(attempt)
        if len(valid) > 1 or not attempts or receipt != (valid[0] if valid else attempts[-1]):
            raise ValueError("Recovery must preserve the first valid answer; successful answers cannot be repeated or selected.")
    recomputed = summarize_external(manifest, receipts, requested, actual_model=actual)
    if (previous["systems"]["valid_responses"] != recomputed["systems"]["valid_responses"]
            or previous["recorded_requests"] != len(receipts) or previous["manifest_sha256"] != digest(manifest)):
        raise ValueError("Saved summary differs from its logical responses.")
    pending = []
    for item in manifest["items"]:
        receipt = by_id[item["id"]]
        try:
            if receipt.get("error"):
                raise ValueError(receipt["error"])
            distribution(item, receipt, actual)
        except (ValueError, TypeError, AttributeError, KeyError):
            pending.append(item)
    if not pending:
        raise ValueError("No invalid items remain; recovery would unnecessarily repeat valid answers.")
    native = client or NativeClient(model_key=model_key)
    if native.model != requested or not native.accepts_model(actual):
        native.__exit__()
        raise ValueError("Recovery configured model differs from the original run.")
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_bytes((source / "manifest.json").read_bytes())
    (output / "original-responses.jsonl").write_bytes((source / "responses.jsonl").read_bytes())
    subset = {**manifest, "items": pending, "recovery_of_manifest_sha256": digest(manifest)}
    repair_summary = run_external(
        subset, output / "repair", client=native, model_key=model_key, min_interval=min_interval,
    )
    repairs = [json.loads(line) for line in (output / "repair" / "responses.jsonl").read_text(encoding="utf-8").splitlines()]
    for receipt in repairs:
        item = items[receipt["id"]]
        expected = digest({"model": requested, "state": item["state"], "questions": {"decision": item["question"]}})
        if receipt.get("request_sha256") != expected:
            raise ValueError("Recovery changed a frozen request.")
        by_id[receipt["id"]] = receipt
    history.extend(repairs)
    effective = [by_id[item["id"]] for item in manifest["items"]]
    for filename, values in (("responses.jsonl", effective), ("attempt-history.jsonl", history)):
        (output / filename).write_text(
            "".join(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n" for value in values), encoding="utf-8",
        )
    summary = summarize_external(manifest, effective, requested, actual_model=actual)
    summary.update(
        model_key=model_key, completed_at=repair_summary["completed_at"], execution_complete=True,
        status="complete" if summary["systems"]["valid_responses"] == len(items) else "failed",
        logical_items=len(items), physical_requests=len(history),
        user_directed_repair={
            "source_directory": source.name, "target_ids": [item["id"] for item in pending],
            "initial_valid_items": recomputed["systems"]["valid_responses"],
            "new_physical_requests": len(repairs), "valid_answers_were_not_repeated": True,
            "first_pass_completed_at": previous["completed_at"],
        },
        minimum_request_interval_seconds=min_interval,
        new_requests_http_keepalive=repair_summary["new_requests_http_keepalive"],
        network_error_policy="explicit_recovery_only; no_automatic_retry",
    )
    physical_latency = [receipt["seconds"] for receipt in history]
    invalid_attempts = 0
    for receipt in history:
        try:
            if receipt.get("error"):
                raise ValueError(receipt["error"])
            distribution(items[receipt["id"]], receipt, actual)
        except (ValueError, TypeError, AttributeError, KeyError):
            invalid_attempts += 1
    summary["failed_physical_requests"] = invalid_attempts
    summary["physical_request_latency"] = {
        "n": len(history), "mean_seconds": statistics.mean(physical_latency),
        "p50_seconds": percentile(physical_latency, 0.5), "p95_seconds": percentile(physical_latency, 0.95),
        "sum_request_seconds": sum(physical_latency),
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    write_report(summary, output / "report.md")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", choices=MODEL_KEYS, help="Explicit model selection; hosted calls may be billed.")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--export-prefix", type=Path)
    parser.add_argument("--reference-summary", type=Path, help="Require the frozen dataset used by a historical result.")
    parser.add_argument("--continue-from", type=Path, help="Explicitly continue only unattempted items into a NEW directory; never resend saved attempts.")
    parser.add_argument("--min-interval", type=float, default=0.0, help="Minimum seconds between request starts; excluded from measured request latency.")
    parser.add_argument("--continue-on-network-errors", action="store_true", help="Record isolated network errors and move to NEXT item, never retry; stop after 3 consecutive errors. HTTP errors still stop.")
    parser.add_argument("--fresh-connections", action="store_true", help="Use new HTTPS connections instead of the default keepalive; TLS overhead is part of request latency.")
    parser.add_argument("--repair-invalid-from", type=Path, help="User-directed recovery of ONLY invalid answers into a new directory; retain all original attempts.")
    args = parser.parse_args()
    if args.report_only and args.continue_from:
        parser.error("--continue-from is a live operation, not --report-only.")
    if args.repair_invalid_from and (args.report_only or args.continue_from):
        parser.error("--repair-invalid-from cannot be combined with --report-only or --continue-from.")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.reference_summary:
        from .external_data import validate_reference
        validate_reference(manifest, json.loads(args.reference_summary.read_text(encoding="utf-8")))
    if args.report_only:
        saved = json.loads((args.output / "manifest.json").read_text(encoding="utf-8"))
        if digest(saved) != digest(manifest):
            raise ValueError("Report input differs from the saved manifest.")
        receipts = [json.loads(line) for line in (args.output / "responses.jsonl").read_text(encoding="utf-8").splitlines()]
        previous = json.loads((args.output / "summary.json").read_text(encoding="utf-8"))
        summary = summarize_external(
            manifest, receipts, previous.get("requested_model", TARGET_MODEL), actual_model=previous["model"],
        )
        summary["completed_at"] = previous["completed_at"]
        for field in (
            "model_key", "status", "execution_complete", "minimum_request_interval_seconds",
            "new_requests_http_keepalive", "continuation",
            "network_error_policy",
            "probability_reporting",
            "logical_items", "physical_requests", "failed_physical_requests",
            "user_directed_repair", "physical_request_latency",
        ):
            if field in previous:
                summary[field] = previous[field]
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        write_report(summary, args.output / "report.md")
    else:
        if args.model is None:
            parser.error("--model is required for live evaluation; --report-only never calls a model.")
        if args.repair_invalid_from:
            summary = repair_invalid_items(
                manifest, args.repair_invalid_from, args.output, model_key=args.model,
                min_interval=args.min_interval,
            )
        else:
            summary = run_external(
                manifest, args.output, model_key=args.model,
                continue_from=args.continue_from, min_interval=args.min_interval,
                continue_on_network_errors=args.continue_on_network_errors,
                fresh_connections=args.fresh_connections,
            )
    if args.export_prefix:
        args.export_prefix.parent.mkdir(parents=True, exist_ok=True)
        args.export_prefix.with_name(args.export_prefix.name + "-summary.json").write_text(
            json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        write_report(summary, args.export_prefix.with_name(args.export_prefix.name + "-report.md"))
    print(json.dumps({suite: {key: values.get(key) for key in ("n", "valid", "accuracy", "spearman", "p50_seconds", "p95_seconds")}
                      for suite, values in summary["suites"].items()}, indent=2))
    return 0 if (summary["recorded_requests"] == summary["total_requests"]
                 and summary["systems"]["valid_responses"] == summary["total_requests"]) else 1


if __name__ == "__main__":
    sys.exit(main())