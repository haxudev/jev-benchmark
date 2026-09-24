"""内网模型 SDK 合约与传输安全测试；不访问真实服务。"""

import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from typesafe_sdk import Choice, TypeSafeAPIConnectionError

from jev_benchmark import ModelError
from jev_benchmark.intranet import IntranetClient, is_safe_base_url

NO_ENV = Path("nonexistent-test-env")


class IntranetTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "INTRANET_BASE_URL": "http://192.168.1.10:8082",
            "INTRANET_API_KEY": "unit-test-secret",
            "INTRANET_MODEL": "football-decision-v2",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    @patch("jev_benchmark.intranet.TypeSafeClient")
    def test_sdk_choice_and_context_cleanup(self, sdk):
        answer = SimpleNamespace(choice="B", confidence=0.8, probabilities={"A": 0.2, "B": 0.8})
        inner = sdk.return_value.__enter__.return_value
        inner.system_one.return_value = SimpleNamespace(model="football-decision-v2", choices={"interpretation": answer})
        client = IntranetClient(NO_ENV)
        self.assertEqual(client.name, "football-decision-v2")
        result = client.choose("虚构对话", "问题", {"A": "一", "B": "二"})
        self.assertEqual(result.selected, "B")
        self.assertEqual(sdk.call_args.kwargs["retry"].max_retries, 0)
        self.assertEqual(sdk.call_args.kwargs["timeout"], 60)
        self.assertEqual(sdk.call_args.kwargs["model"], "football-decision-v2")
        call = inner.system_one.call_args.kwargs
        self.assertEqual(call["state"], "虚构对话")
        choice = call["questions"]["interpretation"]
        self.assertIsInstance(choice, Choice)
        self.assertEqual(choice.instructions, "问题")
        self.assertEqual(choice.criteria, {"A": "一", "B": "二"})
        sdk.return_value.__exit__.assert_called_once()
        self.assertNotIn("unit-test-secret", repr(client))

    def test_http_only_for_private_or_loopback_ip(self):
        for value in ("https://decision.example.com", "http://192.168.1.10:8082", "http://10.0.0.5",
                      "http://127.0.0.1:8000", "http://localhost:8000"):
            self.assertTrue(is_safe_base_url(value), value)
        for value in ("http://example.com", "http://8.8.8.8:8082", "http://intranet.local", "ftp://192.168.1.10",
                      "https://user:secret@example.com", "https://example.com?key=secret", "http://192.168.1.10:bad"):
            with self.subTest(value=value), patch.dict(os.environ, {"INTRANET_BASE_URL": value}):
                with self.assertRaises(ModelError):
                    IntranetClient(NO_ENV)

    @patch("jev_benchmark.intranet.TypeSafeClient")
    def test_safe_connection_error_and_missing_choice(self, sdk):
        inner = sdk.return_value.__enter__.return_value
        inner.system_one.side_effect = TypeSafeAPIConnectionError("unit-test-secret")
        client = IntranetClient(NO_ENV)
        with self.assertRaises(ModelError) as caught:
            client.choose("对话", "问题", {"A": "一"})
        self.assertNotIn("unit-test-secret", str(caught.exception))
        inner.system_one.side_effect = None
        inner.system_one.return_value = SimpleNamespace(model="football-decision-v2", choices={})
        with self.assertRaises(ModelError):
            client.choose("对话", "问题", {"A": "一"})


if __name__ == "__main__":
    unittest.main()
