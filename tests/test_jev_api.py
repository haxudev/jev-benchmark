"""Jev 官方 API 合约及密钥保护测试；不访问网络或真实 .env。"""

import copy
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import httpx

from jev_benchmark import ModelError
from jev_benchmark.jev_api import DEFAULT_ENDPOINT, JevClient

NO_ENV = Path("nonexistent-test-env")


class JevAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(os.environ, {"JEV_API_KEY": "test-secret", "JEV_ENDPOINT": DEFAULT_ENDPOINT})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = JevClient(NO_ENV)
        self.options = {"A": "解释一", "B": "解释二"}
        self.data = {
            "model": "jev-test",
            "answers": {"interpretation": {
                "type": "choice", "choice": "B", "confidence": 0.7,
                "probabilities": {"B": 0.8, "A": 0.2},
            }},
        }

    @patch("jev_benchmark.jev_api.httpx.post")
    def test_request_and_result(self, post) -> None:
        post.return_value = httpx.Response(200, json=self.data)
        result = self.client.choose("虚构对话", "言下之意是什么？", self.options)
        self.assertEqual(result.selected, "B")
        self.assertEqual(result.probabilities, {"A": 0.2, "B": 0.8})
        self.assertEqual(result.confidence, 0.7)
        self.assertEqual(result.model, "jev-test")
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["json"], {
            "model": "jev-latest", "state": "虚构对话",
            "questions": {"interpretation": {
                "type": "choice", "instructions": "言下之意是什么？", "criteria": self.options,
            }},
        })
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-secret")
        self.assertFalse(kwargs["follow_redirects"])
        self.assertEqual(kwargs["timeout"], 60.0)

    def test_env_file_precedence_and_default_endpoint(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text('JEV_API_KEY="file-secret"\n')
            with patch.dict(os.environ, {}, clear=True):
                client = JevClient(path)
                self.assertEqual(client._key, "file-secret")
                self.assertEqual(client._endpoint, DEFAULT_ENDPOINT)
                with patch.dict(os.environ, {"JEV_API_KEY": "override-secret"}):
                    self.assertEqual(JevClient(path)._key, "override-secret")
            self.assertNotIn("file-secret", repr(client))

    def test_missing_or_unsafe_config(self) -> None:
        for updates in (
            {"JEV_API_KEY": ""},
            {"JEV_ENDPOINT": "http://api.typesafe.ai/v1/systemone"},
            {"JEV_ENDPOINT": "https://api.typesafe.ai/v1/systemone?key=secret"},
            {"JEV_ENDPOINT": "https://user:pass@api.typesafe.ai/v1/systemone"},
        ):
            with self.subTest(updates=updates), patch.dict(os.environ, updates):
                with self.assertRaises(ModelError):
                    JevClient(NO_ENV)

    @patch("jev_benchmark.jev_api.httpx.post")
    def test_safe_errors(self, post) -> None:
        for status in (302, 401, 429, 500):
            post.return_value = httpx.Response(status, text="test-secret")
            with self.subTest(status=status), self.assertRaises(ModelError) as caught:
                self.client.choose("对话", "问题", self.options)
            self.assertIn(str(status), str(caught.exception))
            self.assertNotIn("test-secret", str(caught.exception))
        for error in (httpx.ReadTimeout("test-secret"), httpx.ConnectError("test-secret")):
            post.side_effect = error
            with self.assertRaises(ModelError) as caught:
                self.client.choose("对话", "问题", self.options)
            self.assertNotIn("test-secret", str(caught.exception))

    @patch("jev_benchmark.jev_api.httpx.post")
    def test_rejects_malformed_responses(self, post) -> None:
        invalid = [[], {}, {"answers": {}}]
        for field, value in (
            ("choice", "Z"), ("type", "score"), ("confidence", None),
            ("probabilities", {"A": 1.0}),
            ("probabilities", {"A": 0.2, "B": 0.2}),
            ("probabilities", {"A": True, "B": 0}),
            ("probabilities", {"A": -0.1, "B": 1.1}),
            ("probabilities", {"A": "0.2", "B": 0.8}),
        ):
            data = copy.deepcopy(self.data)
            data["answers"]["interpretation"][field] = value
            invalid.append(data)
        for data in invalid:
            with self.subTest(data=data):
                post.return_value = httpx.Response(200, json=data)
                with self.assertRaises(ModelError):
                    self.client.choose("对话", "问题", self.options)
        post.return_value = httpx.Response(200, text="not-json")
        with self.assertRaises(ModelError):
            self.client.choose("对话", "问题", self.options)


if __name__ == "__main__":
    unittest.main()
