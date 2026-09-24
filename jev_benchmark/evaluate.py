"""运行评测、统计成绩并渲染 HTML 报表。"""

from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
from itertools import combinations
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Protocol

from . import DATA_PATH, RESULTS_DIR, Decision, ModelError

CONTESTANTS = ("local", "jev", "intranet")
GROUP_FIELDS = ("subset", "category", "phenomenon")


class Contestant(Protocol):
    key: str
    name: str

    def choose(self, state: str, question: str, options: dict[str, str]) -> Decision: ...


def load_contestant(key: str) -> Contestant:
    # 按需导入：只测 API 时不必加载本地模型。
    if key == "local":
        from .local_model import LocalModel
        return LocalModel()
    if key == "jev":
        from .jev_api import JevClient
        return JevClient()
    if key == "intranet":
        from .intranet import IntranetClient
        return IntranetClient()
    raise ValueError(f"未知模型 {key!r}；可选：{', '.join(CONTESTANTS)}。")


def result_path(keys: Sequence[str]) -> Path:
    return RESULTS_DIR / f"{'-'.join(keys)}.json"


def _rate(matches: int, total: int) -> dict:
    return {"matches": matches, "total": total, "rate": matches / total}


def _check_decision(decision: Decision, options: dict[str, str], name: str) -> None:
    p = decision.probabilities
    if (
        decision.selected not in options or set(p) != set(options)
        or not all(math.isfinite(v) and 0 <= v <= 1 for v in p.values())
        or not math.isclose(sum(p.values()), 1, abs_tol=1e-3)
    ):
        raise ModelError(f"{name} 返回的选择或概率分布无效。")


def summarize(results: list[dict], names: Sequence[str]) -> dict:
    if not results or not names or len(set(names)) != len(names):
        raise ValueError("汇总需要非空结果和不重复的模型名。")
    if len({row["id"] for row in results}) != len(results):
        raise ValueError("结果题号不能重复。")
    for row in results:
        if set(row["decisions"]) != set(names):
            raise ValueError("每道题必须包含全部参评模型；不能把缺失结果当成错误答案。")
    summary = {}
    for name in names:
        correct = lambda row: row["decisions"][name]["selected"] == row["reference"]
        groups = {}
        for field in GROUP_FIELDS:
            groups[field] = {}
            for group in sorted({row[field] for row in results}):
                subset = [row for row in results if row[field] == group]
                groups[field][group] = _rate(sum(correct(r) for r in subset), len(subset))
        summary[name] = {
            **_rate(sum(correct(row) for row in results), len(results)),
            "groups": groups,
            "actual_models": sorted({row["decisions"][name]["model"] for row in results}),
        }
    pairwise = [
        {"models": [left, right], **_rate(sum(
            row["decisions"][left]["selected"] == row["decisions"][right]["selected"] for row in results
        ), len(results))}
        for left, right in combinations(names, 2)
    ]
    unanimous = [row for row in results if len({row["decisions"][n]["selected"] for n in names}) == 1]
    return {
        "reference_agreement": summary,
        "pairwise_agreement": pairwise,
        "unanimous": {
            **_rate(len(unanimous), len(results)),
            "all_correct": sum(row["decisions"][names[0]]["selected"] == row["reference"] for row in unanimous),
            "all_wrong": sum(row["decisions"][names[0]]["selected"] != row["reference"] for row in unanimous),
        },
        "disagreement_ids": [row["id"] for row in results if row not in unanimous],
    }


def summarize_contrast_pairs(results: list[dict], dataset: dict, names: Sequence[str]) -> dict:
    """一对中的两题都与参考一致才算通过，不能仅凭选项字母不同判定。"""
    by_id = {row["id"]: row for row in results}
    pairs = dataset.get("contrast_pairs", [])
    if not pairs:
        raise ValueError("当前题集没有上下文对照题标注。")
    seen = set()
    details = []
    for pair in pairs:
        ids = pair["ids"]
        if len(ids) != 2 or len(set(ids)) != 2 or any(case_id in seen for case_id in ids):
            raise ValueError("上下文对照题必须为不重复的二元题号对。")
        if any(case_id not in by_id for case_id in ids):
            raise ValueError("上下文对照题的模型结果不完整。")
        seen.update(ids)
        passed = {
            name: all(by_id[i]["decisions"][name]["selected"] == by_id[i]["reference"] for i in ids)
            for name in names
        }
        details.append({"ids": ids, "shared_utterance": pair["shared_utterance"], "passed": passed})
    return {
        "by_model": {name: _rate(sum(pair["passed"][name] for pair in details), len(details)) for name in names},
        "pairs": details,
    }


def run_benchmark(
    dataset_path: Path,
    contestants: Sequence[Contestant],
    output_path: Path,
    progress: Callable[[int, int], None] | None = None,
) -> dict:
    """逐题顺序调用各模型；每次调用后写 .partial.json，全部成功后原子替换为完整结果。"""
    raw = dataset_path.read_bytes()
    dataset = json.loads(raw)
    cases = dataset["cases"]
    names = [c.name for c in contestants]
    if not cases or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("题集不能为空，题号必须唯一。")
    if not names or len(set(names)) != len(names):
        raise ValueError("参评模型不能为空且名称不能重复。")
    report = {
        "benchmark": dataset["name"], "version": dataset["version"],
        "dataset_sha256": sha256(raw).hexdigest(), "question": dataset["question"],
        "models": names, "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(), "results": [],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = output_path.with_name(output_path.stem + ".partial.json")
    save = lambda: partial_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    save()
    for case in cases:
        row = {key: case[key] for key in ("id", "title", "category", "phenomenon", "subset", "reference")}
        row["decisions"] = {}
        report["results"].append(row)
        for contestant in contestants:
            start = perf_counter()
            try:
                decision = contestant.choose(case["state"], dataset["question"], case["options"])
                _check_decision(decision, case["options"], contestant.name)
            except (ModelError, ValueError):
                report.update(status="failed", failed_case=case["id"], failed_model=contestant.name)
                save()
                raise
            row["decisions"][contestant.name] = {**asdict(decision), "seconds": perf_counter() - start}
            save()
        if progress is not None:
            progress(len(report["results"]), len(cases))
    report.update(
        status="complete", executed_at=datetime.now(timezone.utc).isoformat(),
        summary=summarize(report["results"], names),
    )
    if dataset.get("contrast_pairs"):
        report["contrast_pairs"] = summarize_contrast_pairs(report["results"], dataset, names)
    save()
    partial_path.replace(output_path)
    return report


def load_results(dataset_path: Path = DATA_PATH, results_dir: Path = RESULTS_DIR) -> dict[str, dict]:
    """按文件名返回与当前题集哈希一致的完整结果；跳过未完成或基于旧题集的文件。"""
    digest = sha256(dataset_path.read_bytes()).hexdigest()
    reports = {}
    for path in sorted(results_dir.glob("*.json")):
        if path.name.endswith(".partial.json"):
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("status") == "complete" and report.get("dataset_sha256") == digest:
            reports[path.name] = report
    return reports


_STYLE = (
    "<style>.jev-benchmark{font:14px/1.65 system-ui;max-width:1400px}"
    ".jev-benchmark table{border-collapse:collapse;width:100%;margin:12px 0}"
    ".jev-benchmark th,.jev-benchmark td{border:1px solid #94a3b8;padding:8px;text-align:left}"
    ".jev-benchmark th{background:#e2e8f0;color:#0f172a}"
    ".jev-benchmark small{opacity:.8}.jev-benchmark summary{cursor:pointer;font-weight:600;padding:10px}"
    ".jev-benchmark pre{white-space:pre-wrap}.jev-benchmark details{border:1px solid #94a3b8;margin:10px 0}"
    ".jev-benchmark .note{border-left:4px solid #2563eb;padding:10px 16px}</style>"
)


def _e(value) -> str:
    return escape(str(value), quote=True)


def _table(headers, rows) -> str:
    return (
        "<table><thead><tr>" + "".join(f"<th>{_e(h)}</th>" for h in headers)
        + "</tr></thead><tbody>"
        + "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
        + "</tbody></table>"
    )


def _rate_cell(value) -> str:
    return f"<b>{value['rate']:.1%}</b> <small>({value['matches']}/{value['total']})</small>"


def render_leaderboard(reports: dict[str, dict], dataset: dict) -> str:
    """每个模型一行，取最近一次完整结果，按参考一致率排序。"""
    subsets = dataset.get("subsets", {})
    latest = {}
    for file, report in reports.items():
        stats = summarize(report["results"], report["models"])["reference_agreement"]
        contrast = summarize_contrast_pairs(report["results"], dataset, report["models"])["by_model"]
        for name in report["models"]:
            if name not in latest or report["executed_at"] > latest[name]["executed_at"]:
                latest[name] = {"file": file, "executed_at": report["executed_at"],
                                "stats": stats[name], "contrast": contrast[name]}
    if not latest:
        return "<div class='jev-benchmark'><p>results/ 中没有与当前题集一致的完整结果。</p></div>"
    rows = [
        [_e(name), _e(", ".join(item["stats"]["actual_models"])), _rate_cell(item["stats"]),
         *(_rate_cell(item["stats"]["groups"]["subset"][key]) for key in subsets),
         _rate_cell(item["contrast"]), _e(item["file"]), _e(item["executed_at"][:10])]
        for name, item in sorted(latest.items(), key=lambda pair: -pair[1]["stats"]["rate"])
    ]
    return (
        f"<div class='jev-benchmark'>{_STYLE}<h3>排行榜 · {_e(dataset['name'])} v{_e(dataset['version'])}</h3>"
        + _table(["模型", "实际版本", "参考一致率", *subsets.values(), "同末句对照（整对）", "结果文件", "日期"], rows)
        + "</div>"
    )


def render_report(report: dict, dataset: dict) -> str:
    if report.get("status") != "complete":
        raise ValueError("不能为未完成的评测生成排行榜。")
    if (
        report["version"] != dataset["version"] or report["question"] != dataset["question"]
        or [row["id"] for row in report["results"]] != [case["id"] for case in dataset["cases"]]
    ):
        raise ValueError("结果与题集版本、问题或题号不匹配。")
    names = tuple(report["models"])
    stats = summarize(report["results"], names)
    cases = {case["id"]: case for case in dataset["cases"]}
    subset_labels = dataset.get("subsets", {})
    e, table, rate = _e, _table, _rate_cell

    def prediction(row, name) -> str:
        decision = row["decisions"][name]
        selected = decision["selected"]
        correct = selected == row["reference"]
        color = "#166534" if correct else "#b91c1c"
        return (
            f"<span style='color:{color};font-weight:600'>{e(selected)} {'✓' if correct else '✗'}</span>"
            f" <small>p={decision['probabilities'][selected]:.1%}</small>"
        )

    def matrix(rows) -> str:
        return table(["题号", "场景", "类型", "参考", *names], [
            [e(row["id"]), e(row["title"]), e(row["phenomenon"]), e(row["reference"]),
             *(prediction(row, name) for name in names)] for row in rows
        ])

    ranked = sorted(names, key=lambda name: -stats["reference_agreement"][name]["rate"])
    subsets = list(stats["reference_agreement"][names[0]]["groups"]["subset"])
    html = [
        "<div class='jev-benchmark'>",
        _STYLE,
        f"<h2>{'单模型评测' if len(names) == 1 else f'{len(names)} 模型同题对比'} · {len(report['results'])} 题</h2>",
        f"<p>{e(report['benchmark'])} v{e(report['version'])} · UTC {e(report['executed_at'])}</p>",
        "<p class='note'><b>两个指标不要混淆：</b>参考一致率 = 模型选择与编写者参考相同；"
        "模型一致率 = 两个模型选择相同（可能一起答错）。所有模型使用同一问题和 A/B/C/D，参考答案不作为输入。"
        "本题集为合成小样本，未经独立人工复核，不代表理解真实伴侣意图的准确率。</p>",
        "<h3>1. 总榜：与编写者参考的一致率</h3>",
        table(["模型", "实际返回版本", "参考一致率", *(subset_labels.get(s, s) for s in subsets)], [
            [e(name), e(", ".join(stats["reference_agreement"][name]["actual_models"])),
             rate(stats["reference_agreement"][name]),
             *(rate(stats["reference_agreement"][name]["groups"]["subset"][s]) for s in subsets)]
            for name in ranked
        ]),
        "<h3>2. 语义类型与主题</h3>",
    ]
    for field, label in (("phenomenon", "语义类型"), ("category", "主题")):
        groups = stats["reference_agreement"][names[0]]["groups"][field]
        html.append(table([label, *names], [
            [e(group), *(rate(stats["reference_agreement"][name]["groups"][field][group]) for name in names)]
            for group in groups
        ]))
    if len(names) > 1:
        html.extend([
            "<h3>模型之间的一致率</h3>",
            table(["模型对", "选择一致率"], [
                [e(" ↔ ".join(pair["models"])), rate(pair)] for pair in stats["pairwise_agreement"]
            ]),
            f"<p>所有参评模型选择相同：{rate(stats['unanimous'])}；其中一起答对 {stats['unanimous']['all_correct']} 题，"
            f"一起答错 {stats['unanimous']['all_wrong']} 题。</p>",
        ])
    if dataset.get("contrast_pairs"):
        contrast = summarize_contrast_pairs(report["results"], dataset, names)
        html.extend([
            "<h3>同一句话，不同上下文</h3>",
            "<p>每对两题都与参考一致才算通过；这些题已包含在总题数中。</p>",
            table(["模型", "整对通过率"], [[e(name), rate(contrast["by_model"][name])] for name in names]),
            table(["同一句话", "对照题号", *names], [
                [e(pair["shared_utterance"]), e(" / ".join(pair["ids"])),
                 *("两题均对 ✓" if pair["passed"][name] else "至少一题不符 ✗" for name in names)]
                for pair in contrast["pairs"]
            ]),
        ])
    focus_rows = (
        [row for row in report["results"] if row["id"] in stats["disagreement_ids"]]
        if len(names) > 1 else
        [row for row in report["results"] if row["decisions"][names[0]]["selected"] != row["reference"]]
    )
    html.extend([
        f"<h3>{'分歧题' if len(names) > 1 else '与参考不一致的题'} · {len(focus_rows)} 题</h3>",
        "<p>✓ / ✗ 表示是否与参考一致；p 是所选候选项概率，不是 API confidence。</p>",
        matrix(focus_rows) if focus_rows else "<p>本项没有题目。</p>",
        "<details><summary>展开全部题目的判断对照</summary>",
        matrix(report["results"]), "</details>",
        "<details><summary>展开逐题对话、选项概率和参考解释</summary>",
    ])
    for row in report["results"]:
        case = cases[row["id"]]
        html.extend([
            f"<details><summary>{e(row['id'])} · {e(row['title'])}</summary>",
            f"<pre>{e(case['state'])}</pre>",
            table(["选项", "解释", *names], [
                [e(letter), e(text), *(f"{row['decisions'][name]['probabilities'][letter]:.2%}" for name in names)]
                for letter, text in case["options"].items()
            ]),
            table(["模型", "判断", "API confidence"], [
                [e(name), prediction(row, name),
                 "不提供" if row["decisions"][name]["confidence"] is None else f"{row['decisions'][name]['confidence']:.2%}"]
                for name in names
            ]),
            f"<p><b>编写者参考：{e(case['reference'])}</b> · {e(case['reason'])}</p></details>",
        ])
    html.extend([
        "</details>",
        f"<p><small>题集 SHA-256：{e(report['dataset_sha256'])}。高候选概率或 API confidence 均不是读懂真实心理的证明。</small></p>",
        "</div>",
    ])
    return "".join(html)
