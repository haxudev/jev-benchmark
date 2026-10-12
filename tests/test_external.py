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
from jev_benchmark.external_data import convert_row, reverse_options, sample_rows, validate_reference
from jev_benchmark.compare import compare_external, external_report


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

        with NativeClient(httpx.MockTransport(handler), env_path=Path("nonexistent-test-env")) as client:
            receipt = client.request("context", questions)
        self.assertEqual(len(calls), 1)
        self.assertEqual(receipt["response"], raw)
        self.assertNotIn("unit-test-secret", repr(receipt))

    def test_failure_is_not_retried_or_echoed(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(422, json={"detail": "unit-test-secret"})

        with NativeClient(httpx.MockTransport(handler), env_path=Path("nonexistent-test-env")) as client:
            receipt = client.request("context", {"q": {"type": "noul", "instructions": "True?"}})
        self.assertEqual(len(calls), 1)
        self.assertEqual(receipt["error"], "http_422")
        self.assertNotIn("unit-test-secret", repr(receipt))

    def test_wrong_model_fails_before_network(self):
        with patch.dict(os.environ, {"INTRANET_MODEL": "jev-latest"}):
            with self.assertRaises(ModelError):
                NativeClient(env_path=Path("nonexistent-test-env"))


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
        native.model = TARGET_MODEL
        native.accepts_model = lambda actual: actual == TARGET_MODEL
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

    def test_requested_alias_and_actual_model_are_separate(self):
        item = self.item()
        receipt = self.receipt({"type": "choice", "choice": "a", "probabilities": {"a": 0.8, "b": 0.2}})
        receipt["response"]["model"] = "microsoft-decision-1"
        receipt["request_sha256"] = digest({
            "model": "Decision-1", "state": item["state"], "questions": {"decision": item["question"]},
        })
        summary = summarize_external({"items": [item]}, [receipt], "Decision-1", actual_model="microsoft-decision-1")
        self.assertEqual(summary["model"], "microsoft-decision-1")
        self.assertEqual(summary["requested_model"], "Decision-1")
        self.assertEqual(summary["systems"]["valid_responses"], 1)
        self.assertIn("hosted API", summary["systems"]["cost_basis"])
        with self.assertRaisesRegex(ValueError, "frozen request"):
            summarize_external({"items": [item]}, [receipt])

    def test_invalid_reversal_keeps_full_pair_denominator(self):
        item = self.item()
        reversed_item = reverse_options(item)
        receipt = self.receipt({"type": "choice", "choice": "a", "probabilities": {"a": 0.8, "b": 0.2}})
        summary = summarize_external({"items": [item, reversed_item]}, [receipt])
        values = summary["option_reversal"]["fixture"]
        self.assertEqual(values["total_pairs"], 1)
        self.assertEqual(values["valid_pairs"], 0)
        self.assertEqual(values["same_choice_rate"], 0)

    def test_reference_manifest_and_external_comparison_integrity(self):
        item = self.item()
        manifest = {"items": [item]}
        receipt = self.receipt({"type": "choice", "choice": "a", "probabilities": {"a": 0.8, "b": 0.2}})
        summary = summarize_external(manifest, [receipt])
        summary["completed_at"] = "2026-10-02T00:00:00Z"
        validate_reference(manifest, summary)
        with self.assertRaises(ValueError):
            validate_reference({"items": [{**item, "state": "changed"}]}, summary)
        comparison = compare_external({"fixture.json": summary})
        self.assertEqual(comparison["models"][TARGET_MODEL]["valid_responses"], 1)
        self.assertIn("N/A", external_report(comparison))
        changed = {**summary, "model": "Decision-1", "manifest_sha256": "wrong"}
        with self.assertRaises(ValueError):
            compare_external({"fixture.json": summary, "changed.json": changed})

    def test_invalid_result_cannot_be_reported_as_complete(self):
        item = self.item()
        native = unittest.mock.MagicMock()
        native.model = TARGET_MODEL
        native.accepts_model = lambda actual: actual == TARGET_MODEL
        native.__enter__.return_value.request.return_value = {
            "seconds": 0.2, "response": {"model": TARGET_MODEL, "answers": {}},
        }
        with tempfile.TemporaryDirectory() as directory:
            summary = run_external({"items": [item]}, Path(directory) / "run", client=native)
        self.assertEqual(summary["status"], "failed")
        self.assertEqual(summary["systems"]["valid_responses"], 0)

    def test_microsoft_transport_and_offline_recompute(self):
        item = self.item()
        calls = []

        def handler(request):
            calls.append(request)
            self.assertEqual(json.loads(request.content)["model"], "Decision-1")
            return httpx.Response(200, json={"model": "microsoft-decision-1", "answers": {"decision": {
                "type": "choice", "choice": "a", "probabilities": {"a": 0.8, "b": 0.2},
            }}})

        with patch.dict(os.environ, {
            "MICROSOFT_ENDPOINT": "https://example.com/providers/microsoft/v1/systemone",
            "MICROSOFT_API_KEY": "fixture-secret", "MICROSOFT_MODEL": "Decision-1",
        }), tempfile.TemporaryDirectory() as directory:
            native = NativeClient(
                httpx.MockTransport(handler), model_key="microsoft", env_path=Path("nonexistent-test-env"),
            )
            output = Path(directory) / "run"
            summary = run_external({"items": [item]}, output, client=native, model_key="microsoft")
            receipts = [json.loads(line) for line in (output / "responses.jsonl").read_text().splitlines()]
            recomputed = summarize_external(
                {"items": [item]}, receipts, summary["requested_model"], actual_model=summary["model"],
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(summary["status"], "complete")
        self.assertEqual(summary["suites"], recomputed["suites"])
        self.assertNotIn("fixture-secret", repr(summary))

    def test_incomplete_comparison_does_not_display_zero_benchmark_scores(self):
        item = self.item()
        summary = summarize_external({"items": [item]}, [])
        summary["completed_at"] = "2026-10-12T00:00:00Z"
        summary["status"] = "failed"
        self.assertEqual(summary["suites"]["fixture"]["accuracy"], 0)
        self.assertEqual(summary["suites"]["fixture"]["status"], "unattempted")
        comparison = compare_external({"failed.json": summary})
        self.assertEqual(comparison["refresh_status"], "partial")
        report = external_report(comparison)
        row = next(line for line in report.splitlines() if line.startswith("| fixture |"))
        self.assertIn("unattempted | N/A |", row)

    def test_systemic_http_error_stops_without_retry_or_new_requests(self):
        items = [self.item(), {**self.item(), "id": "next"}]
        native = unittest.mock.MagicMock()
        native.model = TARGET_MODEL
        native.accepts_model = lambda actual: actual == TARGET_MODEL
        native.__enter__.return_value.request.return_value = {
            "seconds": 0.1, "http_status": 429, "error": "http_429",
        }
        with tempfile.TemporaryDirectory() as directory:
            summary = run_external({"items": items}, Path(directory) / "run", client=native)
        self.assertEqual(native.__enter__.return_value.request.call_count, 1)
        self.assertEqual(summary["recorded_requests"], 1)
        self.assertEqual(summary["status"], "failed")
        self.assertEqual(summary["suites"]["fixture"]["errors"], {"http_429": 1, "unattempted": 1})

    def test_explicit_continuation_never_resends_a_failed_attempt(self):
        items = [{**self.item(), "id": f"item-{index}", "state": f"state-{index}"} for index in range(3)]
        manifest = {"items": items}
        native = unittest.mock.MagicMock()
        native.model = TARGET_MODEL
        native.accepts_model = lambda actual: actual == TARGET_MODEL
        calls = []

        def request(state, questions):
            calls.append(state)
            receipt = {"seconds": 0.1, "request_sha256": digest({
                "model": TARGET_MODEL, "state": state, "questions": questions,
            })}
            if state == "state-0":
                return {**receipt, "http_status": 429, "error": "http_429"}
            return {**receipt, "response": {"model": TARGET_MODEL, "answers": {"decision": {
                "type": "choice", "choice": "a", "probabilities": {"a": 0.8, "b": 0.2},
            }}}}

        native.__enter__.return_value.request.side_effect = request
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "source", Path(directory) / "continued"
            run_external(manifest, source, client=native)
            original = (source / "responses.jsonl").read_bytes()
            summary = run_external(manifest, output, client=native, continue_from=source)
            self.assertEqual((source / "responses.jsonl").read_bytes(), original)
            self.assertEqual(len(list((output / "attempts").glob("*.json"))), 3)
            receipts = [json.loads(line) for line in (output / "responses.jsonl").read_text().splitlines()]
        self.assertEqual(calls, ["state-0", "state-1", "state-2"])
        self.assertEqual(receipts[0]["error"], "http_429")
        self.assertEqual(summary["recorded_requests"], 3)
        self.assertEqual(summary["systems"]["valid_responses"], 2)
        self.assertTrue(summary["execution_complete"])
        self.assertEqual(summary["continuation"]["retained_errors"], 1)
        self.assertEqual(summary["continuation"]["new_requests"], 2)
        summary["completed_at"] = "2026-10-12T00:00:00Z"
        report = external_report(compare_external({"continued.json": summary}))
        self.assertIn("| failed | 0.6667 |", report)

    def test_continuation_rejects_an_attempt_without_a_response_before_network(self):
        items = [{**self.item(), "id": f"item-{index}"} for index in range(2)]
        native = unittest.mock.MagicMock()
        native.model = TARGET_MODEL
        native.accepts_model = lambda actual: actual == TARGET_MODEL
        native.__enter__.return_value.request.return_value = {
            "seconds": 0.1, "http_status": 429, "error": "http_429",
            "request_sha256": digest({
                "model": TARGET_MODEL, "state": items[0]["state"], "questions": {"decision": items[0]["question"]},
            }),
        }
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            run_external({"items": items}, source, client=native)
            native.__enter__.return_value.request.reset_mock()
            (source / "attempts" / "00001.json").write_text("{}")
            output = Path(directory) / "continued"
            with self.assertRaisesRegex(ValueError, "lacks a response"):
                run_external({"items": items}, output, client=native, continue_from=source)
            self.assertFalse(output.exists())
            native.__enter__.return_value.request.assert_not_called()

    def test_request_pacing_does_not_change_receipt_latency(self):
        items = [{**self.item(), "id": f"item-{index}"} for index in range(2)]
        native = unittest.mock.MagicMock()
        native.model = TARGET_MODEL
        native.accepts_model = lambda actual: actual == TARGET_MODEL
        native.__enter__.return_value.request.return_value = {
            "seconds": 0.1, "response": {"model": TARGET_MODEL, "answers": {"decision": {
                "type": "choice", "choice": "a", "probabilities": {"a": 0.8, "b": 0.2},
            }}},
        }
        with tempfile.TemporaryDirectory() as directory, patch(
            "jev_benchmark.external.perf_counter", side_effect=[0.0, 0.2, 1.0],
        ), patch("jev_benchmark.external.sleep") as wait:
            summary = run_external({"items": items}, Path(directory) / "paced", client=native, min_interval=1.0)
        self.assertAlmostEqual(wait.call_args.args[0], 0.8)
        self.assertAlmostEqual(summary["systems"]["mean_seconds"], 0.1)

    def test_isolated_network_errors_move_to_next_item_without_retry(self):
        items = [{**self.item(), "id": f"item-{index}", "state": f"state-{index}"} for index in range(4)]
        native = unittest.mock.MagicMock()
        native.model = TARGET_MODEL
        native.accepts_model = lambda actual: actual == TARGET_MODEL
        calls = []

        def request(state, questions):
            calls.append(state)
            if state in ("state-0", "state-2"):
                return {"seconds": 0.1, "error": "connection_error_no_retry"}
            return {"seconds": 0.1, "response": {"model": TARGET_MODEL, "answers": {"decision": {
                "type": "choice", "choice": "a", "probabilities": {"a": 0.8, "b": 0.2},
            }}}}

        native.__enter__.return_value.request.side_effect = request
        with tempfile.TemporaryDirectory() as directory, patch("jev_benchmark.external.sleep"):
            summary = run_external(
                {"items": items}, Path(directory) / "run", client=native, continue_on_network_errors=True,
            )
        self.assertEqual(calls, ["state-0", "state-1", "state-2", "state-3"])
        self.assertEqual(summary["recorded_requests"], 4)
        self.assertEqual(summary["systems"]["valid_responses"], 2)
        self.assertTrue(summary["execution_complete"])
        self.assertEqual(summary["suites"]["fixture"]["errors"], {"connection_error_no_retry": 2})

    def test_consecutive_network_errors_stop_systemic_failure(self):
        items = [{**self.item(), "id": f"item-{index}"} for index in range(4)]
        native = unittest.mock.MagicMock()
        native.model = TARGET_MODEL
        native.accepts_model = lambda actual: actual == TARGET_MODEL
        native.__enter__.return_value.request.return_value = {"seconds": 0.1, "error": "connection_error_no_retry"}
        with tempfile.TemporaryDirectory() as directory, patch("jev_benchmark.external.sleep"):
            summary = run_external(
                {"items": items}, Path(directory) / "run", client=native, continue_on_network_errors=True,
            )
        self.assertEqual(native.__enter__.return_value.request.call_count, 3)
        self.assertFalse(summary["execution_complete"])
        self.assertEqual(summary["recorded_requests"], 3)

    def test_completed_source_cannot_trigger_more_paid_requests(self):
        native = unittest.mock.MagicMock()
        native.model = TARGET_MODEL
        native.accepts_model = lambda actual: actual == TARGET_MODEL
        native.__enter__.return_value.request.return_value = {
            "seconds": 0.1, "response": {"model": TARGET_MODEL, "answers": {"decision": {
                "type": "choice", "choice": "a", "probabilities": {"a": 0.8, "b": 0.2},
            }}},
        }
        manifest = {"items": [self.item()]}
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "complete"
            run_external(manifest, source, client=native)
            with patch("jev_benchmark.external.NativeClient") as factory:
                with self.assertRaisesRegex(ValueError, "incomplete run"):
                    run_external(manifest, Path(directory) / "must-not-run", continue_from=source)
                factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()