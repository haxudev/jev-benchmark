# jev-benchmark

面向**语义决策模型**的评测项目，对比 **TypeSafe Jev、Microsoft Decision-1、Qwen3.5-4B-Jev**。

内部题集包含100道中文婚恋多轮对话，评估模型能否结合上下文识别真实意图；外部评测覆盖9个任务。模型通过原生 Choice、Noul、Score 接口返回结构化决策，不接收参考答案或评分信息。

## 内部评测 · 100道言下之意题

| 模型 | 实际版本 | 参考一致率 | 婚恋议题 | 女友暗示 | 同末句整对 |
| --- | --- | ---: | ---: | ---: | ---: |
| TypeSafe Jev | `jev-1.13.0` | **100/100，100%** | 50/50 | 50/50 | 10/10 |
| Microsoft Decision-1 | `microsoft-decision-1` | **99/100，99%** | 49/50 | 50/50 | 10/10 |
| [Qwen3.5-4B-Jev](https://huggingface.co/xuhaodev/Qwen3.5-4B-Jev) | `qwen35-4b-jev-v1` | **99/100，99%** | 50/50 | 49/50 | 10/10 |

Jev、Microsoft 为2026-10-12测试结果，Qwen 使用2026-10-02已有结果。Microsoft 与 Qwen 的分歧题分别为 `love-018`、`love-073`，两者选择一致率98%；一致不等于正确。

**[逐题对比](results/three-models-20261012-complete-internal.json)** · [Jev结果](results/jev-20261012.json) · [Microsoft结果](results/microsoft-20261012.json) · [Qwen结果](results/qwen35-4b.json)

<a name="外部评测--qwen35-4b-jev"></a>

## 外部评测 · 三模型对比

每个模型均有 **1,431道主评测题＋90道选项反序对照＝1,521道有效题**。三个模型使用相同的固定版本数据、提示模板和采样清单；Qwen 使用已有结果。

| 任务 | 题量 | TypeSafe Jev | Microsoft Decision-1 | Qwen3.5-4B-Jev |
| --- | ---: | --- | --- | --- |
| JevBench easy | 48 | **48/48，100%** | **48/48，100%** | 48/48，100% |
| JevBench original | 72 | 71/72，98.6% | **72/72，100%** | 68/72，94.4% |
| JevBench hard | 111 | 80/111，72.1% | **91/111，82.0%** | 61/111，55.0% |
| AG News 新闻分类 | 200 | 174/200，87.0% | **179/200，89.5%** | 165/200，82.5% |
| BoolQ 阅读真假判断 | 200 | **180/200，90.0%** | 173/200，86.5% | 166/200，83.0% |
| ANLI 自然语言推断 | 200 | **143/200，71.5%** | 127/200，63.5% | 96/200，48.0% |
| SST-5 五级情感 | 200 | 52.0%；MAE 0.598 | **53.0%；MAE 0.552** | 42.5%；MAE 0.679 |
| STS-B 语义相似度 | 200 | Spearman 0.901；MAE 0.506 | **Spearman 0.930；MAE 0.447** | Spearman 0.878；MAE 0.600 |
| Belebele 中文阅读 | 200 | 188/200，94.0% | **194/200，97.0%** | 169/200，84.5% |

| 反序对照 | TypeSafe Jev | Microsoft Decision-1 | Qwen3.5-4B-Jev |
| --- | ---: | ---: | ---: |
| 有效对数 | 90/90 | 90/90 | 90/90 |
| 选择一致率 | 89/90，98.9% | **90/90，100%** | 90/90，100% |
| 两次均正确 | 75/90，83.3% | **81/90，90.0%** | 68/90，75.6% |

题数与HTTP请求数分开统计：外部有效题均为1,521道，实际请求数分别为 Jev 1,521、Microsoft 1,537、Qwen 1,521。完整记录和指标见报告。

**[完整对比报告](results/three-models-20261012-complete-external-report.md)** · **[机器可读汇总](results/three-models-20261012-complete-external-summary.json)** · [Jev报告](results/jev-20261012-continued-external-report.md) · [Microsoft报告](results/microsoft-20261012-recovered-external-report.md) · [Qwen报告](results/qwen35-4b-external-report.md)

## 耗时对比 · 仅成功请求

单位为 **ms**。仅统计返回有效结构化结果的成功请求，包含答案正确或错误的情况；HTTP错误、超时、无效响应、请求间隔及中断等待均不计入。

### 内部100题

| 模型 | 成功样本数 | 均值 | p50 | p90 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| TypeSafe Jev | 100 | 844.5 | 786.5 | 919.0 | 1,128.6 | 1,879.6 |
| Microsoft Decision-1 | 100 | 1,759.9 | 1,608.1 | 2,194.2 | 2,303.3 | 6,288.5 |
| Qwen3.5-4B-Jev | 100 | 635.4 | 633.9 | 646.2 | 650.3 | 666.1 |

### 外部1,431＋90题

| 模型 | 成功样本数 | 均值 | p50 | p90 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| TypeSafe Jev | 1,521 | 267.4 | 253.5 | 286.5 | 307.8 | 575.2 |
| Microsoft Decision-1 | 1,521 | 1,274.1 | 1,308.5 | 1,730.1 | 1,900.0 | 2,406.4 |
| Qwen3.5-4B-Jev | 1,521 | 539.8 | 422.2 | 未记录 | 652.5 | 未记录 |

Qwen 外部历史记录仅保存均值、p50、p95，缺少逐题耗时，无法准确重算 p90、p99。部署、测试日期和连接方式不同，这些是客户端HTTP耗时，**不是同硬件纯推理速度比较**。

[详细耗时报告](results/successful-latency-comparison.md) · [机器可读耗时](results/successful-latency-comparison.json)

## 评测说明

- 内部题集：[data/implicit_intent.json](data/implicit_intent.json)，v1.0.0。婚恋议题与女友暗示各50题，5种语义类型各20题；10组同末句对照要求两题均正确。
- 外部范围为 JevBench 231道公开题与六个数据集的确定性切片，不是完整 JevBench 榜单或37项学术评测。ANLI 三轮分别取67/67/66题，其余数据集各200题。
- 参考一致率、模型间一致率和反序一致率是不同指标。STS-B 使用 Spearman 与 MAE，不报告分类准确率。详细报告另含 Brier、NLL、ECE 和风险—覆盖率。
- Jev 的概率与 Score 保留API两位小数原值，不归一化；舍入零概率会影响 NLL，不宜与全精度结果直接排名。
- 客户端耗时包含网络和连接开销，不代表同硬件纯推理速度。内部题集为合成小样本，不能推广为通用决策能力或真实伴侣心理判断。

外部清单 SHA-256：

```text
fbb21679cd930b0397a3adcc20d408e422cb816596f0921673ef5602621d4d02
```

Qwen 发布版本为 [`f5864f83`](https://huggingface.co/xuhaodev/Qwen3.5-4B-Jev/tree/f5864f83a4b09a242b5d7b8061c9c76eec4f3062)，版本与训练信息见 [provenance](results/qwen35-4b-provenance.json)。题目未用于本轮模型调整，历史训练数据重叠未被全面排除，部署权重哈希未远程独立核验。

## 快速开始

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

填写 `.env` 后，可运行内部评测。远程调用可能计费，输出路径须不存在：

```powershell
.\.venv\Scripts\python.exe -m jev_benchmark --models jev --output results\jev-new.json
.\.venv\Scripts\python.exe -m jev_benchmark --models microsoft --output results\microsoft-new.json
```

外部数据与评测：

```powershell
.\.venv\Scripts\python.exe -m jev_benchmark.external_data --output data\external-new.json --per-dataset 200 --reference-summary results\qwen35-4b-external-summary.json
.\.venv\Scripts\python.exe -m jev_benchmark.external data\external-new.json --model jev --output results\external-jev-new --export-prefix results\jev-new-external --reference-summary results\qwen35-4b-external-summary.json
```

Microsoft 使用 `--model microsoft` 并指定独立输出目录。默认不自动重试；高级选项见 `python -m jev_benchmark.external --help`。

[benchmark.ipynb](benchmark.ipynb) 默认离线查看保存结果；运行模型需显式启用 `RUN_LIVE`。CLI 提供 `--report-only` 和 `jev_benchmark.compare` 用于离线统计，不调用模型。

## 配置

| 变量 | 说明 |
| --- | --- |
| `JEV_API_KEY` | TypeSafe Jev 密钥 |
| `JEV_ENDPOINT` | 默认 `https://api.typesafe.ai/v1/systemone` |
| `JEV_MODEL` | 默认 `jev-latest`；本次固定 `jev-1.13.0` |
| `MICROSOFT_API_KEY` | Microsoft provider 密钥 |
| `MICROSOFT_ENDPOINT` | 完整接口地址，见 `.env.example`，无需追加路径 |
| `MICROSOFT_MODEL` | 默认 `Decision-1`，实际版本 `microsoft-decision-1` |
| `INTRANET_BASE_URL`、`INTRANET_API_KEY`、`INTRANET_MODEL` | Qwen 自托管服务配置，模型名 `qwen35-4b-jev-v1` |

环境变量优先于 `.env`。密钥、外部原题和原始响应均被 Git 忽略；公开文件只包含结果及汇总。HTTPS 不允许内嵌凭据，明文HTTP只允许私有网段或本机IP。

## 测试与许可

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

代码采用 [MIT](LICENSE)，内部题集采用 [CC BY 4.0](data/LICENSE)。外部数据与模型遵循各自许可；SST-5、STS-B 镜像未明确声明许可，不随仓库分发原题。
