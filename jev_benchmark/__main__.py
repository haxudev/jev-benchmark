"""命令行评测：python -m jev_benchmark --models jev microsoft"""

import argparse
import sys
from pathlib import Path

from . import DATA_PATH, ModelError
from .evaluate import CONTESTANTS, load_contestant, result_path, run_benchmark


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m jev_benchmark", description="在 jev-benchmark 上评测语义决策模型。")
    parser.add_argument(
        "--models", nargs="+", choices=CONTESTANTS, required=True,
        help="显式选择参评模型；每个远程模型发起 100 次请求，可能计费。",
    )
    parser.add_argument("--output", type=Path, help="独立结果文件；不覆盖已有正式结果。")
    args = parser.parse_args(argv)
    keys = list(dict.fromkeys(args.models))
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows 管道默认 cp1252，无法输出中文
    output = args.output or result_path(keys)
    if output.exists() or output.with_name(output.stem + ".partial.json").exists():
        parser.error("输出文件或检查点已存在，请选择新路径；不会自动补跑或覆盖。")
    try:
        contestants = [load_contestant(key) for key in keys]
        report = run_benchmark(
            DATA_PATH, contestants, output,
            lambda done, total: print(f"\r已完成 {done}/{total}", end="", flush=True),
        )
    except ModelError as error:
        parser.exit(1, f"\n错误：{error}\n")
    print()
    for name, stats in report["summary"]["reference_agreement"].items():
        pairs = report["contrast_pairs"]["by_model"][name]
        subsets = " · ".join(f"{k} {v['rate']:.1%}" for k, v in stats["groups"]["subset"].items())
        print(f"{name}: {stats['rate']:.1%} ({stats['matches']}/{stats['total']}) · {subsets} · 对照整对 {pairs['matches']}/{pairs['total']}")
    print(f"结果已保存：{output}")


if __name__ == "__main__":
    main()
