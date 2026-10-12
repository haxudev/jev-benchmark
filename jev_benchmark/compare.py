"""Offline comparison of saved results; never calls a model."""

import argparse
from copy import deepcopy
import json
from pathlib import Path

from .evaluate import merge_results
from .external import latency_statistics

COMPARISON_MODELS = ("Jev-API", "Microsoft Decision", "qwen35-4b-jev-v1")


def internal_latency(report: dict) -> dict[str, dict]:
    if report.get("status") != "complete":
        raise ValueError("Internal latency comparison requires a complete result.")
    return {
        model: latency_statistics([row["decisions"][model]["seconds"] for row in report["results"]])
        for model in report["models"]
    }


def external_success_latency(summary: dict) -> dict:
    systems = summary["systems"]
    if "success_latency" in systems:
        result = deepcopy(systems["success_latency"])
        if result["n"] != systems["valid_responses"] or result["scope"] != "valid_successful_responses_only":
            raise ValueError("Successful latency count or scope differs from valid responses.")
        return result
    # Old summaries cannot recover missing quantiles or remove failed durations without samples.
    all_successful = systems["valid_responses"] == summary["recorded_requests"]
    return {
        "n": systems["valid_responses"],
        **{key: systems.get(key) if all_successful else None for key in (
            "mean_seconds", "p50_seconds", "p90_seconds", "p95_seconds", "p99_seconds",
        )},
        "scope": "valid_successful_responses_only" if all_successful else "unavailable_legacy_mixed_attempts",
        "percentile_method": "historical summary; unrecorded quantiles unavailable",
    }


def latency_table(values: dict[str, dict]) -> str:
    def milliseconds(value):
        return "未记录" if value is None else f"{value * 1000:.1f}"

    lines = ["| 模型 | 成功样本数 | 均值 | p50 | p90 | p95 | p99 |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for model, stats in values.items():
        lines.append(f"| {model} | {stats['n']} | " + " | ".join(
            milliseconds(stats.get(key)) for key in (
                "mean_seconds", "p50_seconds", "p90_seconds", "p95_seconds", "p99_seconds",
            )
        ) + " |")
    return "\n".join(lines) + "\n"


def compare_external(summaries: dict[str, dict], unavailable: dict[str, dict] | None = None) -> dict:
    if not summaries:
        raise ValueError("External comparison requires saved summaries.")
    baseline = next(iter(summaries.values()))
    models = {}
    for filename, summary in summaries.items():
        if (
            summary["manifest_sha256"] != baseline["manifest_sha256"]
            or summary["primary_decisions"] != baseline["primary_decisions"]
            or summary["total_requests"] != baseline["total_requests"]
            or set(summary["suites"]) != set(baseline["suites"])
            or any(summary["suites"][suite]["n"] != baseline["suites"][suite]["n"]
                   for suite in baseline["suites"])
        ):
            raise ValueError(f"External summaries use different frozen datasets: {filename}.")
        model = summary["model"]
        display_name = {
            "jev": "Jev-API", "microsoft": "Microsoft Decision", "intranet": "qwen35-4b-jev-v1",
        }.get(summary.get("model_key"), model)
        if unavailable and display_name in unavailable:
            raise ValueError("A model cannot have both live results and an unavailable status.")
        if model in models:
            raise ValueError("External comparison requires unique models.")
        models[model] = {
            "summary_file": filename, "completed_at": summary["completed_at"],
            "requested_model": summary.get("requested_model", model),
            "recorded_requests": summary["recorded_requests"],
            "logical_items": summary.get("logical_items", summary["total_requests"]),
            "physical_requests": summary.get("physical_requests", summary["recorded_requests"]),
            "failed_physical_requests": summary.get(
                "failed_physical_requests", summary["recorded_requests"] - summary["systems"]["valid_responses"],
            ),
            "valid_responses": summary["systems"]["valid_responses"],
            "execution_complete": summary["recorded_requests"] == summary["total_requests"],
            "status": summary.get("status", "complete" if (
                summary["recorded_requests"] == summary["total_requests"]
                and summary["systems"]["valid_responses"] == summary["total_requests"]
            ) else "failed"),
            "suites": deepcopy(summary["suites"]), "systems": deepcopy(summary["systems"]),
            "option_reversal": deepcopy(summary["option_reversal"]),
            "continuation": deepcopy(summary.get("continuation")),
            "minimum_request_interval_seconds": summary.get("minimum_request_interval_seconds", 0),
            "new_requests_http_keepalive": summary.get("new_requests_http_keepalive"),
            "network_error_policy": summary.get("network_error_policy", "not recorded"),
            "probability_reporting": summary.get("probability_reporting", "not recorded"),
            "user_directed_repair": deepcopy(summary.get("user_directed_repair")),
            "success_latency": external_success_latency(summary),
        }
    return {
        "kind": "offline_comparison", "manifest_sha256": baseline["manifest_sha256"],
        "primary_decisions": baseline["primary_decisions"], "total_requests": baseline["total_requests"],
        "models": models, "unavailable": deepcopy(unavailable or {}),
        "refresh_status": "partial" if unavailable or any(
            values["status"] != "complete" for values in models.values()
        ) else "complete",
    }


def external_report(comparison: dict) -> str:
    def number(value):
        return "N/A" if value is None else f"{value:.4f}"

    models = comparison["models"]
    lines = [
        "# External model comparison", "",
        f"Frozen manifest: `{comparison['manifest_sha256']}`.",
        f"{comparison['primary_decisions']} primary items + "
        f"{comparison['total_requests'] - comparison['primary_decisions']} option reversals per model.", "",
        "Saved results only. Model dates and deployments differ; latency is not normalized hardware performance.",
        "Models without a saved summary are not evaluated here; missing results are not assigned a score.", "",
        f"**Refresh status: {comparison['refresh_status']}**. "
        "Only fully attempted tasks receive benchmark scores below; API failures count as incorrect, "
        "and diagnostic JSON retains incomplete-run metrics.", "",
        "Probability metrics use the reported vectors without renormalization. Jev 1.13 reports hundredths; "
        "its zero-rounding can inflate epsilon-floored NLL relative to full-precision providers. "
        "Ordinal metrics use each API's native Score.", "",
        "| Model | UTC completed | Logical items | Valid items | Physical HTTP attempts | All items attempted | Status | Source |",
        "| --- | --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for model, values in models.items():
        lines.append(f"| {model} | {values['completed_at']} | {values['recorded_requests']} | "
                     f"{values['valid_responses']} | {values['physical_requests']} | {values['execution_complete']} | "
                     f"{values['status']} | {values['summary_file']} |")
    for model, values in comparison.get("unavailable", {}).items():
        lines.append(f"| {model} | Not run | 0 | 0 | 0 | False | {values['status']}: {values['reason']} | "
                     f"{values['status_file']} |")
    for model, values in models.items():
        if values.get("user_directed_repair"):
            recovered = values["user_directed_repair"]
            lines += ["", f"**{model} explicit missing-answer recovery:** "
                      f"{recovered['initial_valid_items']} initial valid items + "
                      f"{recovered['new_physical_requests']} additional attempts. "
                      f"{values['failed_physical_requests']} original failed attempts remain in the audit history; "
                      "valid wrong predictions were not repeated. These are recovered-coverage metrics, not first-pass-only results."]
    lines += [
        "", "## Successful-request latency (ms)", "",
        "Only valid successful responses are included; valid incorrect predictions still count. "
        "Failed requests, invalid responses and all-attempt audit timing are excluded. "
        "Missing historical p90/p99 values are not inferred from p50/p95.", "",
        latency_table({model: values["success_latency"] for model, values in models.items()}),
        "", "## Task metrics", "",
        "| Task | Model | N | Attempted | Valid | Status | Accuracy | Brier (sum) | NLL | ECE | MAE | Spearman | p50 / p95 (s) |",
        "| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for suite in next(iter(models.values()))["suites"]:
        for model, result in models.items():
            values = result["suites"][suite]
            complete = values.get("attempted", values["valid"]) == values["n"]
            score = lambda key: number(values.get(key)) if complete else "N/A"
            attempted = values.get("attempted", values["valid"])
            status = values.get("status", "complete" if complete else "incomplete" if attempted else "unattempted")
            lines.append(f"| {suite} | {model} | {values['n']} | {attempted} | {values['valid']} | {status} | "
                         f"{score('accuracy')} | {score('brier_sum')} | "
                         f"{score('nll_epsilon_1e-15')} | {score('ece_10_equal_width')} | "
                         f"{score('ordinal_mae')} | {score('spearman')} | "
                         f"{number(values['p50_seconds'])} / {number(values['p95_seconds'])} |")
    lines += [
        "", "## Option reversals", "",
        "Rates use all configured pairs; invalid or unattempted pairs do not count as agreement.", "",
        "| Task | Model | Valid / total pairs | Same choice | Both correct |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for model, result in models.items():
        for suite, values in result["option_reversal"].items():
            complete = values["valid_pairs"] == values.get("total_pairs", values["valid_pairs"])
            lines.append(f"| {suite} | {model} | {values['valid_pairs']}/"
                         f"{values.get('total_pairs', values['valid_pairs'])} | "
                         f"{number(values['same_choice_rate']) if complete else 'N/A'} | "
                         f"{number(values['both_correct_rate']) if complete else 'N/A'} |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--internal", type=Path, nargs="+", default=[])
    parser.add_argument("--external", type=Path, nargs="+", default=[])
    parser.add_argument("--unavailable", type=Path, nargs="+", default=[], help="Saved blocked-model status files; never assigned scores.")
    parser.add_argument("--historical-model", nargs="+", choices=COMPARISON_MODELS, default=["qwen35-4b-jev-v1"])
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()
    if not args.internal and not args.external:
        parser.error("Provide saved --internal or --external results.")
    outputs = {}
    unavailable = {}
    for path in args.unavailable:
        status = json.loads(path.read_text(encoding="utf-8"))
        if status.get("status") != "blocked" or status["name"] in unavailable:
            raise ValueError("Unavailable model statuses must be blocked and unique.")
        unavailable[status["name"]] = {**status, "status_file": path.name}
    if args.internal:
        reports = {}
        for path in args.internal:
            if path.name in reports:
                raise ValueError("Input result filenames must be unique.")
            report = json.loads(path.read_text(encoding="utf-8"))
            selected = [model for model in report["models"] if model in COMPARISON_MODELS]
            if not selected:
                raise ValueError(f"No comparison models in {path}.")
            report["models"] = selected
            for row in report["results"]:
                row["decisions"] = {name: row["decisions"][name] for name in selected}
            reports[path.name] = report
        merged = merge_results(reports)
        merged["success_latency"] = internal_latency(merged)
        for name, source in merged["sources"].items():
            source["origin"] = "historical" if name in args.historical_model else "new"
            if name in unavailable:
                if name not in args.historical_model:
                    raise ValueError("A blocked model must be explicitly marked historical for internal comparison.")
                source["refresh_status"] = "blocked"
                source["refresh_reason"] = unavailable[name]["reason"]
        merged["refresh_status"] = "partial" if unavailable else "complete"
        outputs["-internal.json"] = json.dumps(merged, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.external:
        if len({path.name for path in args.external}) != len(args.external):
            raise ValueError("Input summary filenames must be unique.")
        summaries = {path.name: json.loads(path.read_text(encoding="utf-8")) for path in args.external}
        comparison = compare_external(summaries, unavailable)
        outputs["-external-summary.json"] = json.dumps(comparison, indent=2, allow_nan=False) + "\n"
        outputs["-external-report.md"] = external_report(comparison)
    paths = {suffix: args.output_prefix.with_name(args.output_prefix.name + suffix) for suffix in outputs}
    if any(path.exists() for path in paths.values()):
        raise FileExistsError("Comparison outputs already exist; choose a new prefix.")
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    for suffix, content in outputs.items():
        paths[suffix].write_text(content, encoding="utf-8")
        print(paths[suffix])


if __name__ == "__main__":
    main()
