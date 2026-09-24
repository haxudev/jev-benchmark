"""命令行评测：python -m jev_benchmark [--models local jev intranet]"""

import argparse
import sys

from . import DATA_PATH, ModelError
from .evaluate import CONTESTANTS, load_contestant, result_path, run_benchmark


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m jev_benchmark", description="在 jev-benchmark 上评测语义决策模型。")
    parser.add_argument(
        "--models", nargs="+", choices=CONTESTANTS, default=["local"],
        help="参评模型，默认仅 local；jev 与 intranet 每次全量运行各发起 100 次远程请求。",
    )
    keys = list(dict.fromkeys(parser.parse_args(argv).models))
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows 管道默认 cp1252，无法输出中文
    output = result_path(keys)
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
