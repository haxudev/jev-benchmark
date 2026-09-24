"""本地模型 Qwen3.5-0.8B-Jev：读取首个生成位置的选项字母 logits，仅在候选项间归一化。"""

from pathlib import Path

import numpy as np
import onnxruntime_genai as og

from . import MODEL_DIR, Decision


def make_prompt(state: str, question: str, options: dict[str, str]) -> str:
    """选项必须从 A 开始且字母连续。"""
    letters = [chr(ord("A") + index) for index in range(len(options))]
    if not options or list(options) != letters or len(options) > 26:
        raise ValueError("Options must be ordered consecutive letters starting at A (up to Z).")
    option_lines = "\n".join(f"{letter}: {description}" for letter, description in options.items())
    return (
        "<|im_start|>user\n"
        f"待评估内容：\n{state}\n\n"
        f"问题：\n{question}\n\n"
        f"选项：\n{option_lines}\n"
        "仅返回选项字母。<|im_end|>\n"
        "<|im_start|>assistant\n<think>\n\n</think>\n\n"
    )


def score_options(
    model: og.Model, tokenizer: og.Tokenizer, state: str, question: str, options: dict[str, str],
) -> dict[str, float]:
    """返回 {选项字母: 概率}；概率未经校准，不是置信度。"""
    input_ids = np.asarray(tokenizer.encode(make_prompt(state, question, options)), dtype=np.int32)
    params = og.GeneratorParams(model)
    params.set_search_options(max_length=len(input_ids) + 1, do_sample=False)
    generator = og.Generator(model, params)
    generator.append_tokens(input_ids)
    raw_logits = np.asarray(generator.get_logits(), dtype=np.float32)
    logits = raw_logits.reshape(-1, raw_logits.shape[-1])[-1]

    token_ids = []
    for letter in options:
        encoded = np.asarray(tokenizer.encode(letter)).reshape(-1)
        if len(encoded) != 1:
            raise ValueError(f"Option {letter} is not a single tokenizer token.")
        token_ids.append(int(encoded[0]))

    candidate_logits = logits[token_ids]
    probabilities = np.exp(candidate_logits - candidate_logits.max())
    probabilities /= probabilities.sum()
    return {letter: float(p) for letter, p in zip(options, probabilities, strict=True)}


class LocalModel:
    key = "local"
    name = "Qwen3.5-0.8B-Jev"

    def __init__(self, model_dir: Path = MODEL_DIR) -> None:
        config = og.Config(str(model_dir))
        # 官方导出目标为 CUDA FP16；这里改用 CPU provider 运行同一份权重。
        config.clear_providers()
        self._model = og.Model(config)
        self._tokenizer = og.Tokenizer(self._model)

    def score(self, state: str, question: str, options: dict[str, str]) -> dict[str, float]:
        return score_options(self._model, self._tokenizer, state, question, options)

    def choose(self, state: str, question: str, options: dict[str, str]) -> Decision:
        probabilities = self.score(state, question, options)
        return Decision(max(probabilities, key=probabilities.get), probabilities, None, self.name)
