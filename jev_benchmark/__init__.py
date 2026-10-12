"""jev-benchmark：面向语义决策模型的中文言下之意评测集。"""

from dataclasses import dataclass
from collections.abc import Sequence
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "implicit_intent.json"
RESULTS_DIR = ROOT / "results"
MODEL_DIR = ROOT / "model"
ENV_PATH = ROOT / ".env"


class ModelError(RuntimeError):
    """可安全展示的模型调用错误；不含密钥、请求头或原始响应。"""


@dataclass(frozen=True)
class Decision:
    selected: str
    probabilities: dict[str, float]
    confidence: float | None
    model: str


def rounded_probability_bounds(values: Sequence[float], model: str) -> tuple[list[float], list[float]] | None:
    """Jev 1.13 reports hundredths; preserve them and validate their feasible unrounded interval."""
    if model != "jev-1.13.0" or not all(
        math.isclose(value * 100, round(value * 100), abs_tol=1e-8, rel_tol=0) for value in values
    ):
        return None
    return ([max(0.0, value - 0.005) for value in values],
            [min(1.0, value + 0.005) for value in values])


def valid_probability_sum(values: Sequence[float], model: str) -> bool:
    bounds = rounded_probability_bounds(values, model)
    if bounds is not None:
        lower, upper = bounds
        return sum(lower) <= 1 + 1e-12 and sum(upper) >= 1 - 1e-12
    return math.isclose(sum(values), 1.0, abs_tol=0.001, rel_tol=0)
