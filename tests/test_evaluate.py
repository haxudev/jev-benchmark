"""评测流程、统计口径、报表与入口的离线测试；使用假模型，不访问任何服务。"""

import copy
from contextlib import redirect_stdout
import io
import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from jev_benchmark import DATA_PATH, ROOT, Decision, ModelError
from jev_benchmark.__main__ import main
from jev_benchmark.evaluate import (
    load_contestant, load_results, render_leaderboard, render_report, result_path, run_benchmark,
    summarize, summarize_contrast_pairs,
)


class FakeModel:
    def __init__(self, name: str, letter: str, fail: bool = False) -> None:
        self.key, self.name, self.letter, self.fail = name.lower(), name, letter, fail
        self.calls = []

    def choose(self, state, question, options):
        self.calls.append((state, question, options))
        if self.fail:
            raise ModelError("测试服务错误")
        probabilities = {letter: 0.1 for letter in options}
        probabilities[self.letter] = 0.7
        return Decision(self.letter, probabilities, 0.6, f"{self.name}-v0")


class EvaluateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    def _run(self, models, output: Path, progress=None):
        with patch("httpx.post", side_effect=AssertionError("禁止联网")):
            return run_benchmark(DATA_PATH, models, output, progress)

    def test_complete_run_metrics_and_render(self):
        models = [FakeModel("Local", "A"), FakeModel("Official", "B"), FakeModel("Intranet", "C")]
        with TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "results.json"
            progress = []
            report = self._run(models, output, lambda n, total: progress.append((n, total)))
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), report)
            self.assertFalse(output.with_name("results.partial.json").exists())
        self.assertEqual(progress[-1], (100, 100))
        expected = [(c["state"], self.dataset["question"], c["options"]) for c in self.dataset["cases"]]
        for model in models:
            self.assertEqual(model.calls, expected)
        stats = report["summary"]
        self.assertEqual([stats["reference_agreement"][m.name]["matches"] for m in models], [26, 26, 24])
        self.assertEqual(stats["reference_agreement"]["Local"]["groups"]["subset"]["girlfriend-hint"]["matches"], 13)
        self.assertTrue(all(pair["matches"] == 0 for pair in stats["pairwise_agreement"]))
        self.assertEqual(len(stats["disagreement_ids"]), 100)
        self.assertEqual(len(report["contrast_pairs"]["pairs"]), 10)
        self.assertNotIn("reason", report["results"][0])

        html = render_report(report, self.dataset)
        for text in ("Local", "Official", "Intranet", "26.0%", "24.0%", "模型之间的一致率", "女友暗示", "love-100"):
            self.assertIn(text, html)
        dataset = copy.deepcopy(self.dataset)
        dataset["cases"][0]["state"] = "<script>alert('x')</script>"
        self.assertNotIn("<script>", render_report(report, dataset))
        self.assertIn("&lt;script&gt;", render_report(report, dataset))
        report["status"] = "failed"
        with self.assertRaises(ValueError):
            render_report(report, self.dataset)

    def test_single_model_report(self):
        with TemporaryDirectory() as directory:
            report = self._run([FakeModel("Local", "A")], Path(directory) / "r.json")
        html = render_report(report, self.dataset)
        self.assertIn("单模型评测", html)
        self.assertIn("与参考不一致的题", html)
        self.assertNotIn("模型之间的一致率", html)

    def test_load_results_and_leaderboard_keep_latest_per_model(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = self._run([FakeModel("Local", "A")], root / "a.json")
            self._run([FakeModel("Local", "C"), FakeModel("Official", "B")], root / "b.json")
            (root / "stale.json").write_text(json.dumps({**old, "dataset_sha256": "0" * 64}), encoding="utf-8")
            (root / "x.partial.json").write_text("{}", encoding="utf-8")
            saved = load_results(DATA_PATH, root)
        self.assertEqual(list(saved), ["a.json", "b.json"])
        html = render_leaderboard(saved, self.dataset)
        self.assertEqual(html.count("<tr>"), 3)
        self.assertNotIn("a.json", html)
        self.assertLess(html.index("Official"), html.index("Local"))
        self.assertIn("24.0%", html)
        self.assertIn("女友暗示", html)
        self.assertIn("没有", render_leaderboard({}, self.dataset))

    def test_load_results_accepts_line_endings_but_rejects_changed_content(self):
        lf = DATA_PATH.read_bytes().replace(b"\r\n", b"\n")
        crlf = lf.replace(b"\n", b"\r\n")
        changed = copy.deepcopy(self.dataset)
        changed["cases"][0]["state"] += "新增上下文。"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            results = root / "results"
            results.mkdir()
            for name, raw in (("lf", lf), ("crlf", crlf), ("changed", json.dumps(changed, ensure_ascii=False).encode())):
                (results / f"{name}.json").write_text(json.dumps({
                    "status": "complete", "dataset_sha256": sha256(raw).hexdigest(),
                }), encoding="utf-8")
            for raw in (lf, crlf):
                with self.subTest(line_ending="CRLF" if b"\r\n" in raw else "LF"):
                    dataset_path = root / "dataset.json"
                    dataset_path.write_bytes(raw)
                    saved = load_results(dataset_path, results)
                    self.assertEqual(set(saved), {"lf.json", "crlf.json"})
                    self.assertEqual(saved["crlf.json"]["dataset_sha256"], sha256(crlf).hexdigest())

    def test_failure_keeps_partial_and_previous_result(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "results.json"
            output.write_text("previous-complete-result", encoding="utf-8")
            with self.assertRaisesRegex(ModelError, "测试服务错误"):
                self._run([FakeModel("Local", "A"), FakeModel("Official", "B"), FakeModel("Intranet", "C", fail=True)], output)
            self.assertEqual(output.read_text(encoding="utf-8"), "previous-complete-result")
            partial = json.loads(output.with_name("results.partial.json").read_text(encoding="utf-8"))
        self.assertEqual(partial["status"], "failed")
        self.assertEqual(partial["failed_model"], "Intranet")
        self.assertEqual(set(partial["results"][0]["decisions"]), {"Local", "Official"})
        self.assertNotIn("summary", partial)

    def test_rejects_invalid_decisions_and_duplicate_names(self):
        class Invalid(FakeModel):
            def choose(self, state, question, options):
                return Decision("Z", {"A": 1.0}, None, "bad")

        with TemporaryDirectory() as directory:
            with self.assertRaises(ModelError):
                self._run([Invalid("Bad", "A")], Path(directory) / "r.json")
            with self.assertRaises(ValueError):
                self._run([FakeModel("Same", "A"), FakeModel("Same", "B")], Path(directory) / "r.json")
        with self.assertRaises(ValueError):
            load_contestant("unknown")

    def test_pairwise_agreement_is_not_reference_agreement(self):
        names = ("L", "J", "I")
        rows = [
            {"id": str(i), "reference": ref, "subset": "s", "category": "c", "phenomenon": "p",
             "decisions": {n: {"selected": p, "model": n} for n, p in zip(names, predictions)}}
            for i, (ref, predictions) in enumerate([
                ("A", ("A", "A", "A")), ("B", ("A", "A", "A")), ("C", ("C", "D", "C")), ("D", ("A", "D", "D")),
            ])
        ]
        stats = summarize(rows, names)
        self.assertEqual([pair["matches"] for pair in stats["pairwise_agreement"]], [2, 3, 3])
        self.assertEqual(stats["unanimous"]["matches"], 2)
        self.assertEqual(stats["unanimous"]["all_correct"], 1)
        self.assertEqual(stats["unanimous"]["all_wrong"], 1)
        del rows[0]["decisions"]["I"]
        with self.assertRaises(ValueError):
            summarize(rows, names)

    def test_contrast_pairs_require_both_answers_correct(self):
        dataset = {"contrast_pairs": [
            {"ids": ["1", "2"], "shared_utterance": "那就按你说的办。"},
            {"ids": ["3", "4"], "shared_utterance": "你记得就好。"},
        ]}
        results = [
            {"id": "1", "reference": "A", "decisions": {"L": {"selected": "A"}}},
            {"id": "2", "reference": "A", "decisions": {"L": {"selected": "A"}}},
            {"id": "3", "reference": "B", "decisions": {"L": {"selected": "C"}}},
            {"id": "4", "reference": "C", "decisions": {"L": {"selected": "D"}}},
        ]
        result = summarize_contrast_pairs(results, dataset, ("L",))
        self.assertEqual(result["by_model"]["L"], {"matches": 1, "total": 2, "rate": 0.5})
        with self.assertRaises(ValueError):
            summarize_contrast_pairs(results[:3], dataset, ("L",))
        dataset["contrast_pairs"].append(dataset["contrast_pairs"][0])
        with self.assertRaises(ValueError):
            summarize_contrast_pairs(results, dataset, ("L",))


class EntryPointTests(unittest.TestCase):
    def test_cli_defaults_to_local_only(self):
        with TemporaryDirectory() as directory, redirect_stdout(io.StringIO()) as output, patch(
            "jev_benchmark.__main__.load_contestant", side_effect=lambda key: FakeModel("Local", "A"),
        ) as load, patch("jev_benchmark.__main__.result_path", return_value=Path(directory) / "local.json"):
            main([])
        load.assert_called_once_with("local")
        self.assertIn("26.0%", output.getvalue())
        self.assertEqual(result_path(["local", "jev"]).name, "local-jev.json")

    def test_notebook_compiles_and_defaults_to_local_only(self):
        notebook = json.loads((ROOT / "benchmark.ipynb").read_text(encoding="utf-8"))
        code = ["".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"]
        for source in code:
            compile(source, "notebook", "exec")
        self.assertEqual(sum('MODELS = ["local"]' in source for source in code), 1)


if __name__ == "__main__":
    unittest.main()
