"""jev-benchmark：面向语义决策模型的中文言下之意评测集。"""

from dataclasses import dataclass
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
