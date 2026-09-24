"""题集结构、均衡性与标注约束检查。"""

from collections import Counter
import json
import re
import unittest

from jev_benchmark import DATA_PATH

TOTAL = 100
MARRIAGE_CATEGORIES = {
    "彩礼与财务", "酒席与仪式", "婚房与产权", "双方父母", "生育与照护",
    "事业与异地", "家务与分工", "信任与隐私", "冲突与修复", "长期承诺",
}
HINT_CATEGORIES = {
    "约会与陪伴", "节日与礼物", "消息与回复", "饮食与点餐", "外表与购物",
    "情绪与身体", "朋友与社交", "异性与醋意", "生活照顾", "关系确认",
}
PHENOMENA = {"反话与讽刺", "借题表达", "间接请求", "试探确认", "回避与保留"}
FIELDS = {"id", "title", "category", "phenomenon", "target_speaker", "subset", "state", "options", "reference", "reason"}


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dataset = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        cls.cases = cls.dataset["cases"]

    def test_metadata(self) -> None:
        self.assertEqual(self.dataset["version"], "1.0.0")
        self.assertEqual(self.dataset["language"], "zh-CN")
        self.assertIn("最后发言者", self.dataset["question"])
        self.assertTrue(self.dataset["description"].strip())
        self.assertEqual(set(self.dataset["subsets"]), {"marriage", "girlfriend-hint"})

    def test_case_schema(self) -> None:
        self.assertEqual([case["id"] for case in self.cases], [f"love-{i:03}" for i in range(1, TOTAL + 1)])
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(set(case), FIELDS)
                for key in FIELDS - {"options"}:
                    self.assertIsInstance(case[key], str)
                    self.assertTrue(case[key].strip())
                self.assertIn(case["subset"], self.dataset["subsets"])
                self.assertEqual(list(case["options"]), list("ABCD"))
                self.assertEqual(len(set(case["options"].values())), 4)
                self.assertIn(case["reference"], case["options"])
                self.assertGreaterEqual(len(case["reason"]), 40)
                dialogue = [line for line in case["state"].splitlines() if line.startswith(("男友：", "女友："))]
                self.assertGreaterEqual(len(dialogue), 6)
                self.assertTrue(dialogue[-1].startswith(case["target_speaker"] + "："))
                self.assertFalse(any("信息不足" in text for text in case["options"].values()), "四个选项都应是实质解释。")
                for quote in re.findall(r"‘([^’]+)’", case["reason"]):
                    self.assertIn(quote, case["state"], "参考解释引用的原文必须能在对话中找到。")

    def test_balance_and_uniqueness(self) -> None:
        self.assertEqual(Counter(c["category"] for c in self.cases), {c: 5 for c in MARRIAGE_CATEGORIES | HINT_CATEGORIES})
        self.assertEqual(Counter(c["phenomenon"] for c in self.cases), {p: 20 for p in PHENOMENA})
        self.assertEqual(Counter(c["target_speaker"] for c in self.cases), {"男友": 25, "女友": 75})
        self.assertEqual(Counter(c["reference"] for c in self.cases), {"A": 26, "B": 26, "C": 24, "D": 24})
        for field in ("id", "title", "state"):
            self.assertEqual(len({case[field] for case in self.cases}), TOTAL)
        for category in MARRIAGE_CATEGORIES | HINT_CATEGORIES:
            self.assertEqual({c["phenomenon"] for c in self.cases if c["category"] == category}, PHENOMENA)

    def test_subsets(self) -> None:
        marriage, hint = self.cases[:50], self.cases[50:]
        self.assertEqual({c["subset"] for c in marriage}, {"marriage"})
        self.assertEqual({c["category"] for c in marriage}, MARRIAGE_CATEGORIES)
        self.assertEqual(Counter(c["target_speaker"] for c in marriage), {"男友": 25, "女友": 25})
        self.assertEqual({c["subset"] for c in hint}, {"girlfriend-hint"})
        self.assertEqual({c["category"] for c in hint}, HINT_CATEGORIES)
        self.assertEqual({c["target_speaker"] for c in hint}, {"女友"})
        self.assertEqual(Counter(c["reference"] for c in hint), {"A": 13, "B": 13, "C": 12, "D": 12})
        for case in hint:
            boyfriend_lines = [line for line in case["state"].splitlines() if line.startswith("男友：")]
            self.assertTrue(any("是不是" in line or "？" in line for line in boyfriend_lines), case["id"])

    def test_contrast_pairs_and_short_final_utterances(self) -> None:
        by_id = {case["id"]: case for case in self.cases}
        pairs = self.dataset["contrast_pairs"]
        self.assertEqual(len(pairs), 10)
        seen = set()
        for pair in pairs:
            self.assertEqual(len(set(pair["ids"])), 2)
            self.assertFalse(set(pair["ids"]) & seen)
            seen.update(pair["ids"])
            left, right = (by_id[i] for i in pair["ids"])
            self.assertEqual(left["target_speaker"], right["target_speaker"])
            self.assertNotEqual(left["options"][left["reference"]], right["options"][right["reference"]])
            for case in (left, right):
                self.assertEqual(case["state"].splitlines()[-1].split("：", 1)[1], pair["shared_utterance"])
        for case in self.cases:
            final_utterance = case["state"].splitlines()[-1].split("：", 1)[1]
            self.assertLessEqual(len(final_utterance), 35)
            for explicit in ("前提是", "我希望", "只要", "我不是"):
                self.assertNotIn(explicit, final_utterance)


if __name__ == "__main__":
    unittest.main()
