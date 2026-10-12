"""Jev 官方托管 API（TypeSafe System One，Choice 协议）。"""

import math
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from dotenv import dotenv_values

from . import ENV_PATH, Decision, ModelError

DEFAULT_ENDPOINT = "https://api.typesafe.ai/v1/systemone"


def read_config(names: tuple[str, ...], env_path: Path = ENV_PATH) -> dict[str, str]:
    """系统环境变量优先于 .env。"""
    values = dotenv_values(env_path, interpolate=False)
    return {name: (os.getenv(name, values.get(name)) or "").strip() for name in names}


def _probability(value: object, source: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ModelError(f"{source} 返回了非数值概率或置信度。")
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ModelError(f"{source} 返回的概率或置信度不在 [0, 1] 内。")
    return float(value)


def parse_choice(data: object, options: dict[str, str], source: str) -> Decision:
    if not isinstance(data, dict):
        raise ModelError(f"{source} 响应不是 JSON 对象。")
    answers = data.get("answers")
    answer = answers.get("interpretation") if isinstance(answers, dict) else None
    if not isinstance(answer, dict) or answer.get("type") != "choice":
        raise ModelError(f"{source} 响应缺少 interpretation Choice 结果。")
    selected = answer.get("choice")
    if not isinstance(selected, str) or selected not in options:
        raise ModelError(f"{source} 返回了候选项之外的选择。")
    raw = answer.get("probabilities")
    if not isinstance(raw, dict) or set(raw) != set(options):
        raise ModelError(f"{source} 概率分布与请求的候选项不一致。")
    probabilities = {letter: _probability(raw[letter], source) for letter in options}
    if not math.isclose(sum(probabilities.values()), 1.0, abs_tol=0.001):
        raise ModelError(f"{source} 候选概率之和不为 1；未擅自归一化。")
    model = data.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ModelError(f"{source} 响应缺少实际模型版本。")
    return Decision(selected, probabilities, _probability(answer.get("confidence"), source), model)


class JevClient:
    key = "jev"
    name = "Jev-API"
    config_prefix = "JEV"
    default_endpoint = DEFAULT_ENDPOINT
    model = "jev-latest"

    def __init__(self, env_path: Path = ENV_PATH) -> None:
        prefix = self.config_prefix
        config = read_config((f"{prefix}_API_KEY", f"{prefix}_ENDPOINT", f"{prefix}_MODEL"), env_path)
        self._key = config[f"{prefix}_API_KEY"]
        self._endpoint = config[f"{prefix}_ENDPOINT"] or self.default_endpoint
        self.model = config[f"{prefix}_MODEL"] or self.model
        if not self._key:
            raise ModelError(f"请在 .env 或环境变量中设置 {prefix}_API_KEY。")
        try:
            url = urlsplit(self._endpoint)
            url.port
            valid = (
                url.scheme == "https" and bool(url.hostname)
                and not (url.username or url.password or url.query or url.fragment)
            )
        except ValueError:
            valid = False
        if not valid:
            raise ModelError(f"{prefix}_ENDPOINT 必须是无内嵌凭据、查询参数或片段的 HTTPS 地址。")

    def accepts_model(self, actual: object) -> bool:
        if self.model != "jev-latest":
            return actual == self.model
        return isinstance(actual, str) and (actual == "jev" or actual.startswith("jev-"))

    def choose(self, state: str, question: str, options: dict[str, str]) -> Decision:
        if not state.strip() or not question.strip() or not options:
            raise ValueError("对话、问题和候选项不能为空。")
        data = self.request(state, {
            "interpretation": {"type": "choice", "instructions": question, "criteria": options},
        })
        decision = parse_choice(data, options, self.name)
        if not self.accepts_model(decision.model):
            raise ModelError(f"{self.name} 返回的实际模型身份不符。")
        return decision

    def request(self, state: object, questions: dict) -> dict:
        payload = {"model": self.model, "state": state, "questions": questions}
        try:
            response = httpx.post(
                self._endpoint,
                headers={"Authorization": f"Bearer {self._key}"},
                json=payload,
                timeout=60.0,
                follow_redirects=False,
            )
        except httpx.TimeoutException:
            raise ModelError(f"{self.name} 请求超时（60 秒），未自动重试。") from None
        except httpx.RequestError:
            raise ModelError(f"{self.name} 连接失败，请检查网络和 {self.config_prefix}_ENDPOINT。") from None
        if not response.is_success:
            raise ModelError(f"{self.name} 请求失败（HTTP {response.status_code}），请检查密钥、额度及服务状态。")
        try:
            data = response.json()
        except ValueError:
            raise ModelError(f"{self.name} 返回了无效 JSON。") from None
        if not isinstance(data, dict):
            raise ModelError(f"{self.name} 响应不是 JSON 对象。")
        return data
