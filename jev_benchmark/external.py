"""Reproducible external evaluation of the native Qwen decision head."""

from hashlib import sha256
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import random
import statistics
import sys
from time import perf_counter
from urllib.parse import urlsplit

import httpx

from . import ModelError
from .intranet import is_safe_base_url
from .jev_api import read_config

TARGET_MODEL = "qwen35-4b-jev-v1"


def digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    return sha256(encoded).hexdigest()


class NativeClient:
    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        config = read_config(("INTRANET_BASE_URL", "INTRANET_API_KEY", "INTRANET_MODEL"))
        base_url = config["INTRANET_BASE_URL"]
        if config["INTRANET_MODEL"] != TARGET_MODEL:
            raise ModelError(f"External evaluation requires INTRANET_MODEL={TARGET_MODEL}.")
        if not is_safe_base_url(base_url) or urlsplit(base_url).hostname == "api.typesafe.ai":
            raise ModelError("External evaluation requires the configured self-hosted endpoint.")
        if not config["INTRANET_API_KEY"]:
            raise ModelError("Missing INTRANET_API_KEY.")
        self._endpoint = base_url.rstrip("/") + "/v1/systemone"
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {config['INTRANET_API_KEY']}"},
            timeout=120.0, follow_redirects=False, transport=transport,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._client.close()

    def request(self, state: object, questions: dict) -> dict:
        payload = {"model": TARGET_MODEL, "state": state, "questions": questions}
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
        except httpx.RequestError:
            receipt["error"] = "connection_error_no_retry"
        receipt["seconds"] = perf_counter() - start
        return receipt


def distribution(item: dict, receipt: dict) -> list[float]:
    response = receipt.get("response")
    if not isinstance(response, dict) or response.get("model") != TARGET_MODEL:
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
    if not math.isclose(sum(probabilities), 1, abs_tol=0.001, rel_tol=0):
        raise ValueError("invalid_probability_sum")
    if kind == "choice":
        selected = answer.get("choice")
        if selected not in labels or probabilities[labels.index(selected)] < max(probabilities) - 1e-8:
            raise ValueError("invalid_choice")
    if kind == "score":
        score = answer.get("score")
        expected = sum(index * value for index, value in enumerate(probabilities))
        if (isinstance(score, bool) or not isinstance(score, (int, float))
                or not math.isfinite(score) or not math.isclose(score, expected, abs_tol=1e-5)):
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
        "p50_seconds": percentile([row["seconds"] for row in valid], 0.5),
        "p95_seconds": percentile([row["seconds"] for row in valid], 0.95),
    }
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


def summarize_external(manifest: dict, receipts: list[dict]) -> dict:
    by_id = {receipt["id"]: receipt for receipt in receipts}
    if len(by_id) != len(receipts) or set(by_id) - {item["id"] for item in manifest["items"]}:
        raise ValueError("Duplicate or unknown response IDs.")
    rows = []
    for item in manifest["items"]:
        receipt = by_id.get(item["id"])
        row = {**item, "valid": False, "correct": False, "attempted": receipt is not None}
        if receipt:
            request_hash = digest({"model": TARGET_MODEL, "state": item["state"], "questions": {"decision": item["question"]}})
            if receipt.get("request_sha256", request_hash) != request_hash:
                raise ValueError("Saved response does not match the frozen request.")
            row["seconds"] = receipt["seconds"]
            try:
                if receipt.get("error"):
                    raise ValueError(receipt["error"])
                probabilities = distribution(item, receipt)
                selected = max(range(len(probabilities)), key=probabilities.__getitem__)
                row.update(valid=True, probabilities=probabilities, selected_index=selected,
                           correct=selected == item.get("gold_index"),
                           expected_score=sum(index * value for index, value in enumerate(probabilities)))
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
    consistency = {suite: {"valid_pairs": len(selected),
                          "same_choice_rate": statistics.mean(row["same_choice"] for row in selected),
                          "both_correct_rate": statistics.mean(row["both_correct"] for row in selected)}
                   for suite in sorted({pair["suite"] for pair in pairs})
                   if (selected := [pair for pair in pairs if pair["suite"] == suite])}
    latency = [receipt["seconds"] for receipt in receipts]
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
            "manifest_sha256": digest(manifest), "model": TARGET_MODEL,
            "primary_decisions": len(primary), "hard_families": families,
            "dataset_sources": manifest.get("sources", []), "protocol": manifest.get("protocol", {}),
            "systems": {"actual_models": sorted({response["model"] for response in responses if isinstance(response.get("model"), str)}),
                        "valid_responses": sum(row["valid"] for row in rows),
                        "mean_seconds": statistics.mean(latency) if latency else None,
                        "p50_seconds": percentile(latency, 0.5), "p95_seconds": percentile(latency, 0.95),
                        "sum_request_seconds": sum(latency),
                        "reported_input_tokens": token_total("input_tokens"),
                        "reported_output_tokens": token_total("output_tokens"),
                        "cost_usd": None, "cost_basis": "self-hosted; GPU cost and power were not measured"}}


def write_report(summary: dict, path: Path) -> None:
    def display(value):
        return "N/A" if value is None else f"{value:.4f}"

    lines = ["# Qwen3.5-4B-Jev External Evaluation", "",
             f"Model: `{TARGET_MODEL}`. Manifest SHA-256: `{summary['manifest_sha256']}`.", "",
             f"Requests recorded: {summary['recorded_requests']}/{summary['total_requests']}.", "",
             "| Suite | N | Valid | Accuracy | Brier (sum) | NLL | ECE | MAE | Spearman | p50 / p95 (s) |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for suite, values in summary["suites"].items():
        lines.append(f"| {suite} | {values['n']} | {values['valid']} | {display(values['accuracy'])} | "
                     f"{display(values.get('brier_sum'))} | {display(values.get('nll_epsilon_1e-15'))} | "
                     f"{display(values.get('ece_10_equal_width'))} | "
                     f"{display(values.get('ordinal_mae'))} | {display(values.get('spearman'))} | "
                     f"{display(values['p50_seconds'])} / {display(values['p95_seconds'])} |")
    lines += ["", "## Interpretation", "",
              "- JevBench results cover only the pinned, published public cohorts, not the full leaderboard.",
              "- Accuracy counts failures and unattempted items as incorrect; probability metrics use valid vectors only.",
              "- Brier uses the multiclass sum convention. NLL floors probabilities at 1e-15 and reports zero-mass rows.",
              "- ECE uses top-label probability and reference agreement, not the model's entropy-based confidence.",
              "- Score tasks retain expected-level MAE and Spearman; continuous STS-B targets have no fabricated gold distribution.",
              "- Risk/coverage curves are descriptive; no threshold or temperature is fitted on these test cases.",
              "- Accuracy intervals resample whole scenario groups (1,000 bootstrap draws).",
              "- Latency is serial client wall time with a loaded self-hosted model, not normalized GPU throughput.",
              "- No model tuning, retry, hidden probability normalization, or paid official Jev calls.",
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
        lines.append(f"| {suite} | {values['valid_pairs']} | {values['same_choice_rate']:.4f} | {values['both_correct_rate']:.4f} |")
    lines += ["", "## High-Probability Decisions", "",
              "Descriptive p_max >= 0.9 slice; these are not fitted deployment thresholds.", "",
              "| Suite | Accepted | Coverage | Error rate |", "| --- | ---: | ---: | ---: |"]
    for suite, values in summary["suites"].items():
        selected = next((entry for entry in values.get("risk_coverage_descriptive", []) if entry["threshold_p_max"] == 0.9), None)
        if selected:
            lines.append(f"| {suite} | {selected['n']} | {selected['coverage']:.4f} | {display(selected['error_rate'])} |")
    lines += ["", "## Systems", "", f"```json\n{json.dumps(summary['systems'], indent=2)}\n```", "",
              "## Data Revisions", "",
              "| Repository | Revision | File | Source license |", "| --- | --- | --- | --- |"]
    for source in summary["dataset_sources"]:
        lines.append(f"| {source['repo']} | {source['revision']} | {source['file']} | {source['license']} |")
    lines += ["", "Raw source text and responses remain local and gitignored; upstream licenses still apply.",
              "Unspecified source licenses are not treated as permission to redistribute."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_external(manifest: dict, output: Path, client=None) -> dict:
    items = manifest["items"]
    if not items or len({item["id"] for item in items}) != len(items):
        raise ValueError("Manifest requires nonempty, unique item IDs.")
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    attempts = output / "attempts"
    attempts.mkdir()
    receipts = []
    with (client or NativeClient()) as native, (output / "responses.jsonl").open("x", encoding="utf-8") as log:
        for index, item in enumerate(items):
            payload = {"model": TARGET_MODEL, "state": item["state"], "questions": {"decision": item["question"]}}
            with (attempts / f"{index:05d}.json").open("x", encoding="utf-8") as marker:
                json.dump({"id": item["id"], "request_sha256": digest(payload),
                           "started_at": datetime.now(timezone.utc).isoformat()}, marker)
            receipt = {"id": item["id"], **native.request(item["state"], {"decision": item["question"]})}
            log.write(json.dumps(receipt, ensure_ascii=False, allow_nan=False) + "\n")
            log.flush()
            receipts.append(receipt)
            if receipt.get("error") and receipt.get("http_status") not in (400, 422):
                print(f"Stopped at {index + 1}/{len(items)}: {receipt['error']}", flush=True)
                break
            response = receipt.get("response")
            if isinstance(response, dict) and response.get("model") != TARGET_MODEL:
                print("Stopped: actual model mismatch.", flush=True)
                break
            if (index + 1) % 25 == 0 or index + 1 == len(items):
                print(f"Recorded {index + 1}/{len(items)}", flush=True)
    summary = summarize_external(manifest, receipts)
    summary["completed_at"] = datetime.now(timezone.utc).isoformat()
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    write_report(summary, output / "report.md")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--export-prefix", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.report_only:
        saved = json.loads((args.output / "manifest.json").read_text(encoding="utf-8"))
        if digest(saved) != digest(manifest):
            raise ValueError("Report input differs from the saved manifest.")
        receipts = [json.loads(line) for line in (args.output / "responses.jsonl").read_text(encoding="utf-8").splitlines()]
        summary = summarize_external(manifest, receipts)
        previous = json.loads((args.output / "summary.json").read_text(encoding="utf-8"))
        summary["completed_at"] = previous["completed_at"]
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        write_report(summary, args.output / "report.md")
    else:
        summary = run_external(manifest, args.output)
    if args.export_prefix:
        args.export_prefix.parent.mkdir(parents=True, exist_ok=True)
        args.export_prefix.with_name(args.export_prefix.name + "-summary.json").write_text(
            json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        write_report(summary, args.export_prefix.with_name(args.export_prefix.name + "-report.md"))
    print(json.dumps({suite: {key: values.get(key) for key in ("n", "valid", "accuracy", "spearman", "p50_seconds", "p95_seconds")}
                      for suite, values in summary["suites"].items()}, indent=2))
    return 0 if summary["recorded_requests"] == summary["total_requests"] else 1


if __name__ == "__main__":
    sys.exit(main())