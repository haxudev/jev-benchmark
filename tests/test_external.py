"""External evaluation contracts; no network or model loading."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx

from jev_benchmark import ModelError
from jev_benchmark.external import NativeClient, TARGET_MODEL, digest, distribution, run_external, summarize_external
from jev_benchmark.external_data import convert_row, reverse_options, sample_rows


class NativeClientTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {
            "INTRANET_BASE_URL": "http://127.0.0.1:18085",
            "INTRANET_API_KEY": "unit-test-secret",
            "INTRANET_MODEL": TARGET_MODEL,
        })
        env.start()
        self.addCleanup(env.stop)

    def test_native_primitives_and_unmodified_response(self):
        calls = []
        questions = {
            "intent": {"type": "choice", "instructions": "Route", "criteria": {"a": "First", "b": "Second"}},
            "truth": {"type": "noul", "instructions": "True?"},
            "level": {"type": "score", "instructions": "Grade", "criteria": ["Low", "High"]},
        }
        raw = {"model": TARGET_MODEL, "answers": {"intent": {
            "type": "choice", "choice": "a", "probabilities": {"a": 0.98, "b": 0.01},
        }}}

        def handler(request):
            calls.append(request)
            self.assertEqual(request.url.path, "/v1/systemone")
            self.assertEqual(json.loads(request.content), {
                "model": TARGET_MODEL, "state": "context", "questions": questions,
            })
            return httpx.Response(200, json=raw)

        with NativeClient(httpx.MockTransport(handler)) as client:
            receipt = client.request("context", questions)
        self.assertEqual(len(calls), 1)
        self.assertEqual(receipt["response"], raw)
        self.assertNotIn("unit-test-secret", repr(receipt))

    def test_failure_is_not_retried_or_echoed(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(422, json={"detail": "unit-test-secret"})

        with NativeClient(httpx.MockTransport(handler)) as client:
            receipt = client.request("context", {"q": {"type": "noul", "instructions": "True?"}})
        self.assertEqual(len(calls), 1)
        self.assertEqual(receipt["error"], "http_422")
        self.assertNotIn("unit-test-secret", repr(receipt))

    def test_wrong_model_fails_before_network(self):
        with patch.dict(os.environ, {"INTRANET_MODEL": "jev-latest"}):
            with self.assertRaises(ModelError):
                NativeClient()


class EvaluationTests(unittest.TestCase):
    def item(self, kind="choice"):
        criteria = {"a": "First", "b": "Second"} if kind == "choice" else ["Low", "High"]
        question = {"type": kind, "instructions": "Judge"}
        if kind != "noul":
            question["criteria"] = criteria
        return {"id": "fixture", "suite": "fixture", "labels": ["a", "b"] if kind == "choice" else ["0", "1"],
                "question": question, "state": "context", "gold": [1.0, 0.0], "gold_index": 0}

    def receipt(self, answer):
        return {"id": "fixture", "seconds": 0.2, "response": {"model": TARGET_MODEL, "answers": {"decision": answer}}}

    def test_noul_score_and_invalid_probability_sum(self):
        self.assertEqual(distribution(self.item("noul"), self.receipt({"type": "noul", "noul": 0.3})), [0.7, 0.3])
        self.assertEqual(distribution(self.item("score"), self.receipt({"type": "score", "score": 0.2,
                         "probabilities": {"0": 0.8, "1": 0.2}})), [0.8, 0.2])
        with self.assertRaisesRegex(ValueError, "invalid_probability_sum"):
            distribution(self.item(), self.receipt({"type": "choice", "choice": "a", "probabilities": {"a": 0.98, "b": 0.01}}))

    def test_metrics_failures_and_raw_persistence(self):
        item = self.item()
        answer = {"type": "choice", "choice": "a", "probabilities": {"a": 0.8, "b": 0.2}}
        receipt = self.receipt(answer)
        manifest = {"items": [item, {**item, "id": "unattempted"}]}
        summary = summarize_external(manifest, [receipt])
        metrics = summary["suites"]["fixture"]
        self.assertEqual(metrics["accuracy"], 0.5)
        self.assertAlmostEqual(metrics["brier_sum"], 0.08)
        self.assertAlmostEqual(metrics["ece_10_equal_width"], 0.2)
        self.assertEqual(metrics["errors"], {"unattempted": 1})
        native = unittest.mock.MagicMock()
        native.__enter__.return_value.request.return_value = receipt
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            run_external({"items": [item]}, output, client=native)
            raw = json.loads((output / "responses.jsonl").read_text())
            self.assertEqual(raw["response"], receipt["response"])
            self.assertEqual(len(list((output / "attempts").glob("*.json"))), 1)
            with self.assertRaises(FileExistsError):
                run_external({"items": [item]}, output, client=native)

    def test_continuous_score_has_no_fabricated_accuracy(self):
        item = {**self.item("score"), "gold": None, "gold_index": None, "target_score": 0.3}
        summary = summarize_external({"items": [item]}, [self.receipt({
            "type": "score", "score": 0.2, "probabilities": {"0": 0.8, "1": 0.2},
        })])
        metrics = summary["suites"]["fixture"]
        self.assertIsNone(metrics["accuracy"])
        self.assertNotIn("brier_sum", metrics)
        self.assertAlmostEqual(metrics["ordinal_mae"], 0.1)

    def test_reversal_preserves_semantics_and_changes_request_hash(self):
        original = self.item()
        reordered = reverse_options(original)
        self.assertEqual(reordered["labels"][reordered["gold_index"]], "a")
        self.assertEqual(original["labels"], ["a", "b"])
        self.assertNotEqual(digest(original["question"]), digest(reordered["question"]))
        receipt = self.receipt({"type": "choice", "choice": "a", "probabilities": {"a": 0.8, "b": 0.2}})
        reverse_receipt = {**receipt, "id": reordered["id"]}
        summary = summarize_external({"items": [original, reordered]}, [receipt, reverse_receipt])
        self.assertEqual(summary["primary_decisions"], 1)
        self.assertEqual(summary["option_reversal"]["fixture"]["same_choice_rate"], 1)

    def test_sampling_and_continuous_label_conversion(self):
        rows = [{"value": index} for index in range(30)]
        self.assertEqual(sample_rows(rows, 5, "fixture"), sample_rows(rows, 10, "fixture")[:5])
        self.assertEqual(len({index for index, row in sample_rows(rows, 10, "fixture")}), 10)
        item = convert_row("stsb", {"sentence1": "one", "sentence2": "two", "score": 0.7}, "stsb-1")
        self.assertEqual(item["target_score"], 3.5)
        self.assertIsNone(item["gold"])
        reading = convert_row("belebele-zho_Hans", {
            "flores_passage": "passage", "question": "question", "correct_answer_num": "4",
            "mc_answer1": "one", "mc_answer2": "two", "mc_answer3": "three", "mc_answer4": "four",
        }, "reading-1")
        self.assertEqual(reading["gold_index"], 3)

    def test_offline_integrity_rejects_duplicate_and_mismatched_receipts(self):
        item = self.item()
        receipt = self.receipt({"type": "choice", "choice": "a", "probabilities": {"a": 0.8, "b": 0.2}})
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            summarize_external({"items": [item]}, [receipt, receipt])
        with self.assertRaisesRegex(ValueError, "frozen request"):
            summarize_external({"items": [item]}, [{**receipt, "request_sha256": "wrong"}])

    def test_malformed_response_is_an_explicit_failure(self):
        summary = summarize_external({"items": [self.item()]}, [{
            "id": "fixture", "seconds": 0.2, "response": ["invalid"],
        }])
        self.assertEqual(summary["suites"]["fixture"]["accuracy"], 0)
        self.assertEqual(summary["suites"]["fixture"]["valid"], 0)
        self.assertIsNone(summary["systems"]["reported_input_tokens"])


if __name__ == "__main__":
    unittest.main()