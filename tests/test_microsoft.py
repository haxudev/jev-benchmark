"""Microsoft native protocol tests; never access real credentials or services."""

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import httpx

from jev_benchmark import ModelError
from jev_benchmark.external import NativeClient
from jev_benchmark.microsoft import MicrosoftClient


class MicrosoftTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {
            "MICROSOFT_ENDPOINT": MicrosoftClient.default_endpoint,
            "MICROSOFT_API_KEY": "fixture-secret", "MICROSOFT_MODEL": "Decision-1",
        })
        env.start()
        self.addCleanup(env.stop)

    def test_native_primitives_and_full_endpoint(self):
        questions = {
            "choice": {"type": "choice", "instructions": "Select", "criteria": {"a": "A", "b": "B"}},
            "truth": {"type": "noul", "instructions": "True?"},
            "level": {"type": "score", "instructions": "Grade", "criteria": ["Low", "High"]},
        }
        calls = []

        def handler(request):
            calls.append(request)
            self.assertEqual(str(request.url), MicrosoftClient.default_endpoint)
            self.assertEqual(request.headers["Authorization"], "Bearer fixture-secret")
            self.assertEqual(json.loads(request.content), {
                "model": "Decision-1", "state": {"context": "fixture"}, "questions": questions,
            })
            return httpx.Response(200, json={"model": "Decision-1", "answers": {}})

        with NativeClient(
            httpx.MockTransport(handler), model_key="microsoft", env_path=Path("nonexistent-test-env"),
        ) as client:
            receipt = client.request({"context": "fixture"}, questions)
        self.assertEqual(len(calls), 1)
        self.assertNotIn("fixture-secret", repr(receipt))

    @patch("jev_benchmark.jev_api.httpx.post")
    def test_choice_and_actual_identity(self, post):
        response = {"model": "microsoft-decision-1", "answers": {"interpretation": {
            "type": "choice", "choice": "a", "probabilities": {"a": 0.8, "b": 0.2}, "confidence": 0.7,
        }}}
        post.return_value = httpx.Response(200, json=response)
        client = MicrosoftClient(Path("nonexistent-test-env"))
        self.assertEqual(client.choose("Context", "Select", {"a": "A", "b": "B"}).model, "microsoft-decision-1")
        response["model"] = "jev-1.13.0"
        post.return_value = httpx.Response(200, json=response)
        with self.assertRaisesRegex(ModelError, "身份不符"):
            client.choose("Context", "Select", {"a": "A", "b": "B"})

    def test_config_and_transport_guards(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("MICROSOFT_API_KEY=file-secret\nMICROSOFT_MODEL=Decision-1\n")
            with patch.dict(os.environ, {}, clear=True):
                client = MicrosoftClient(path)
                self.assertEqual(client._key, "file-secret")
                self.assertEqual(client._endpoint, MicrosoftClient.default_endpoint)
                with patch.dict(os.environ, {"MICROSOFT_API_KEY": "override"}):
                    self.assertEqual(MicrosoftClient(path)._key, "override")
        for endpoint in ("http://example.com", "https://example.com?key=secret", "https://example.com:bad"):
            with self.subTest(endpoint=endpoint), patch.dict(os.environ, {"MICROSOFT_ENDPOINT": endpoint}):
                with self.assertRaises(ModelError):
                    MicrosoftClient(Path("nonexistent-test-env"))

    def test_no_retry_or_error_body_leak(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(429, text="fixture-secret")

        with NativeClient(
            httpx.MockTransport(handler), model_key="microsoft", env_path=Path("nonexistent-test-env"),
        ) as client:
            receipt = client.request("Context", {"q": {"type": "noul", "instructions": "True?"}})
        self.assertEqual(len(calls), 1)
        self.assertEqual(receipt["error"], "http_429")
        self.assertNotIn("fixture-secret", repr(receipt))

    def test_gateway_connection_policy_is_explicit(self):
        with patch("jev_benchmark.external.httpx.Client") as factory:
            client = NativeClient(model_key="microsoft", env_path=Path("nonexistent-test-env"))
            self.assertNotIn("limits", factory.call_args.kwargs)
            fresh = NativeClient(
                model_key="microsoft", env_path=Path("nonexistent-test-env"), fresh_connections=True,
            )
        self.assertEqual(factory.call_args.kwargs["limits"].max_keepalive_connections, 0)
        self.assertTrue(client.http_keepalive)
        self.assertFalse(fresh.http_keepalive)
        client.__exit__()
        fresh.__exit__()
