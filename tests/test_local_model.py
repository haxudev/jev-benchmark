"""提示词格式及仅候选项归一化检查；不加载真实模型。"""

import unittest
from unittest.mock import patch

import numpy as np

from jev_benchmark.local_model import make_prompt, score_options


class FakeTokenizer:
    def encode(self, text: str) -> list[int]:
        return {"A": [4], "B": [9]}.get(text, [1, 2, 3])


class FakeGenerator:
    def __init__(self, model: object, params: object) -> None:
        pass

    def append_tokens(self, input_ids: np.ndarray) -> None:
        pass

    def get_logits(self) -> np.ndarray:
        logits = np.zeros((1, 12), dtype=np.float32)
        logits[0, 4] = 1
        logits[0, 9] = 3
        logits[0, 10] = 99
        return logits


class LocalModelTests(unittest.TestCase):
    def test_prompt_format(self) -> None:
        prompt = make_prompt("你好", "这件事紧急吗？", {"A": "否", "B": "是"})
        self.assertIn("待评估内容：\n你好", prompt)
        self.assertIn("问题：\n这件事紧急吗？", prompt)
        self.assertIn("选项：\nA: 否\nB: 是\n仅返回选项字母。", prompt)
        self.assertTrue(prompt.endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n"))

    def test_rejects_skipped_letters(self) -> None:
        with self.assertRaises(ValueError):
            make_prompt("你好", "请选择", {"A": "一", "C": "三"})

    @patch("jev_benchmark.local_model.og.Generator", FakeGenerator)
    @patch("jev_benchmark.local_model.og.GeneratorParams")
    def test_normalizes_only_candidates(self, _: object) -> None:
        result = score_options(object(), FakeTokenizer(), "你好", "请选择", {"A": "否", "B": "是"})
        self.assertEqual(list(result), ["A", "B"])
        self.assertAlmostEqual(sum(result.values()), 1, places=6)
        self.assertGreater(result["B"], 0.85)


if __name__ == "__main__":
    unittest.main()
