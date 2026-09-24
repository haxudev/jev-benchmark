"""下载固定版本的本地 ONNX 权重，并做一次 CPU 推理自检：python -m jev_benchmark.download"""

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download

from . import MODEL_DIR

MODEL_ID = "lokinfey/Qwen3_5_0.8B_jev"
REVISION = "19409b2d7d18b46a7c22598aa3ac934f493f77d0"
FILES = [
    "model.onnx", "model.onnx.data", "genai_config.json", "tokenizer.json", "tokenizer_config.json",
    "config.json", "model_config.json", "chat_template.jinja", "processor_config.json", "README.md",
]


def download_model(model_dir: Path = MODEL_DIR) -> Path:
    snapshot_download(
        repo_id=MODEL_ID, revision=REVISION, local_dir=model_dir, allow_patterns=FILES, max_workers=4,
    )
    missing = [name for name in FILES if not (model_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Incomplete model download: {', '.join(missing)}")
    return model_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-only", action="store_true", help="跳过推理自检")
    args = parser.parse_args()
    directory = download_model()
    print(f"模型已下载到 {directory}")
    if not args.download_only:
        from .local_model import LocalModel

        result = LocalModel(directory).score(
            "救命！我的付款已经连续 3 天失败了。我今天必须拿到这笔钱。",
            "这条消息是否表达了紧迫性？",
            {"A": "否", "B": "是"},
        )
        print(f"CPU 推理自检（A=否 / B=是）：{result}")
