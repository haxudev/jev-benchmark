# jev-benchmark

面向**语义决策模型**的中文评测集：100 道婚恋送命题多轮对话，检验模型能否结合上下文读出**真实意图**。

本次仅对比 **TypeSafe Jev、Microsoft Decision-1、Qwen3.5-4B-Jev**。调用端不请求自由文本，只使用原生类型化决策：内部题集为 Choice 四选一，外部题集另有 Noul 与 Score。参考答案、解释、标签和评分信息不发送给模型。

## 本轮状态 · 2026-10-12

**本轮不是三模型全量评测完成：**

| 模型 | 内部 100 题 | 外部 1,431＋90 题 | 来源 / 阻塞 |
| --- | --- | --- | --- |
| TypeSafe Jev | 本轮未运行；保留历史参考 | 本轮未运行，没有成绩 | 官方入口探针返回 **HTTP 451**，[状态记录](results/jev-20261012-status.json) |
| Microsoft Decision-1 | **已完成：99/100** | **1,431＋90 题全部已尝试；1,505/1,521 次有效** | 保留 16 次失败：HTTP 429×1、连接错误×2、超时×13；没有重发失败题 |
| Qwen3.5-4B-Jev | 复用已有 99/100 | 复用已有 1,521/1,521 有效结果 | 不重新调用、不调整模型或校准 |

正式调用每题仅一次，**不自动重试、不自动补跑**。用户要求继续执行后，显式续跑只处理尚未尝试的题：原有失败不重发，原目录不覆盖。Jev 已明确返回 `Typesafe is not available in your region.`，需要服务方允许的执行环境，不能通过调整模型参数解决。两份用户密钥仅保存在被 Git 忽略的本地 `.env`，不随仓库分发。

已核对 [官方模型文档](https://docs.typesafe.ai/models.md)，Jev 使用的 endpoint 正确，未找到受支持的区域替代入口；现有 Microsoft 网关也未提供已核实的 Jev 接入。[TypeSafe 客户协议 2.3(g)](https://typesafe.ai/legal/mca) 禁止绕过访问限制，因此不尝试代理改出口、伪装地区或向未经授权的网关转交密钥。完成 Jev 本轮评测需要 TypeSafe 开通允许的访问，或提供服务方授权的执行环境。

## 内部评测 · 100 道言下之意题

| 模型 | 实际返回版本 | 参考一致率 | 婚恋议题 | 女友暗示 | 同末句整对 | 执行日期 / 来源 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| TypeSafe Jev | `jev-1.13.0` | **100/100，100%** | 50/50 | 50/50 | 10/10 | **2026-09-24 历史参考，非本轮刷新** |
| Microsoft Decision-1 | `microsoft-decision-1` | **99/100，99%** | 49/50 | 50/50 | 10/10 | **2026-10-12 本轮新运行** |
| [Qwen3.5-4B-Jev](https://huggingface.co/xuhaodev/Qwen3.5-4B-Jev) | `qwen35-4b-jev-v1` | **99/100，99%** | 50/50 | 49/50 | 10/10 | 2026-10-02 已有发布结果复用 |

Microsoft 与 Qwen 各错一题，但不是同一题：分别为 `love-018`、`love-073`，两者选择一致率为 **98/100**。历史 Jev 与二者分别一致 **99/100**；一致不等于正确，也不能将历史 Jev 成绩视为当前服务的新成绩。

Microsoft 平均客户端耗时约 **1,760 ms/题**；Qwen 原有结果约 **635 ms/题**。两者分别经云端 HTTPS 与内网 HTTP 调用，包含传输和客户端开销，**不是同硬件纯推理速度比较**。

**[三模型离线逐题对比](results/three-models-20261012-final-internal.json)** · **[Microsoft 原始结果](results/microsoft-20261012.json)** · **[Qwen 原始结果](results/qwen35-4b.json)** · **[Qwen 报告](results/qwen35-4b-report.md)**。

合并结果保留每个模型的原始执行时间、题集哈希和来源；`kind=offline_comparison`、`refresh_status=partial` 明确区分“完整同题历史对比”与“本轮刷新受阻”。历史 Jev 来自已有结果文件，只抽取 Jev，不再展示旧小模型对照。

<a name="外部评测--qwen35-4b-jev"></a>

## 外部评测 · 三模型对比

Qwen 于 2026-10-02 完成 **1,431 道主评测题＋90 道选项反序对照**，1,521 次调用全部有效。本轮按固定 revision、采样种子和提示模板重建原清单，SHA-256 精确匹配：

```text
fbb21679cd930b0397a3adcc20d408e422cb816596f0921673ef5602621d4d02
```

Microsoft 初次在第 93 次请求遇到 HTTP 429。服务恢复后，显式续跑只发送尚未尝试题，最终 **1,431 道主评测题＋90 道反序题全部各尝试一次**：主评测 1,415/1,431 有效，反序 90/90 有效，共 **1,505/1,521 有效（98.95%）**。原有错误不被后续成功响应覆盖，16 道失败题均未重发。

**这是完整调用覆盖，不是无故障通过**：机器汇总保留 `execution_complete=true` 与 `status=failed`，区分“所有题均已尝试”和“所有响应均有效”。分类准确率把失败计为错误；概率、MAE、Spearman 只使用有效响应。

| 任务 | 主评测题量 | TypeSafe Jev | Microsoft Decision-1 | MS 有效数 | Qwen3.5-4B-Jev（已有结果） |
| --- | ---: | --- | --- | ---: | --- |
| JevBench easy 公开题 | 48 | 未运行 · HTTP 451 | **48/48，100%** | 48/48 | 48/48，100% |
| JevBench original 公开题 | 72 | 未运行 · HTTP 451 | **71/72，98.6%** | 71/72 | 68/72，94.4% |
| JevBench hard 公开题 | 111 | 未运行 · HTTP 451 | **91/111，82.0%** | 111/111 | 61/111，55.0% |
| AG News 新闻分类 | 200 | 未运行 · HTTP 451 | **178/200，89.0%** | 199/200 | 165/200，82.5% |
| BoolQ 阅读真假判断 | 200 | 未运行 · HTTP 451 | **172/200，86.0%** | 199/200 | 166/200，83.0% |
| ANLI 对抗自然语言推断 | 200 | 未运行 · HTTP 451 | **126/200，63.0%** | 199/200 | 96/200，48.0% |
| SST-5 五级情感 | 200 | 未运行 · HTTP 451 | **105/200，52.5%；MAE 0.550** | 197/200 | 85/200，42.5%；MAE 0.679 |
| STS-B 语义相似度 | 200 | 未运行 · HTTP 451 | **Spearman 0.929；MAE 0.450** | 198/200 | Spearman 0.878；0–5 分 MAE 0.600 |
| Belebele 简体中文阅读 | 200 | 未运行 · HTTP 451 | **188/200，94.0%** | 193/200 | 169/200，84.5% |

| 反序对照 | TypeSafe Jev | Microsoft Decision-1 | Qwen3.5-4B-Jev |
| --- | --- | --- | --- |
| 有效对数 | 未运行 | 90/90 | 90/90 |
| 选择一致率 | 无成绩 | **90/90，100%** | 90/90，100% |
| 两次均正确 | 无成绩 | **81/90，90.0%** | 68/90，75.6% |

JevBench easy 的 p50 / p95：Microsoft **511 / 1,076 ms**，Qwen **444 / 491 ms**。全体请求客户端耗时：Microsoft 平均 **1,457 ms**、p50 **1,310 ms**、p95 **1,911 ms**；Qwen 原有结果平均 **540 ms**、p50 **422 ms**、p95 **653 ms**。Microsoft 包含失败请求耗时，不含请求间隔及中断等待；部分续跑使用新 TLS 连接。云端与内网、连接模式和有效率不同，**不是同硬件纯推理速度比较**。账单金额未测得，不虚构费用。

**[最终外部对比报告](results/three-models-20261012-final-external-report.md)** · **[机器可读对比](results/three-models-20261012-final-external-summary.json)** · **[Microsoft 全量覆盖与失败汇总](results/microsoft-20261012-continued3-external-summary.json)** · **[Microsoft 外部报告](results/microsoft-20261012-continued3-external-report.md)** · **[Qwen 完整外部报告](results/qwen35-4b-external-report.md)** · **[Qwen 汇总](results/qwen35-4b-external-summary.json)**。

初次受限及中间连接故障快照仍保留，例如 [93 次请求的初始汇总](results/microsoft-20261012-external-summary.json)。最终报告不把这些早期部分样本伪装为新的完整模型结果，也不把 Jev 的区域拒绝换算成 0% 成绩。

完整指标保留 Brier（多分类求和）、NLL、ECE、按场景分组的 bootstrap 区间、MAE、Spearman 和描述性风险—覆盖率。JSON 为审计保留“失败及未尝试题按错误计入预定分母”的严格准确率；尚未尝试完整题集的任务在展示中标为 N/A，全部尝试后的 API 错误按错误计分并明确给出有效数。概率指标只使用有效响应。STS-B 不伪造分类准确率或参考概率分布。

范围是固定 revision 的 JevBench **231 道已发布题**及六个公开数据集的确定性切片，**不是完整 JevBench v1.5 榜单，也不是 37 项学术评测的完整复现**。ANLI 三轮分别取 67/67/66 题，其余任务各取 200 题。Qwen 的 ANLI ECE 为 0.437、SST-5 ECE 为 0.446；不能把婚恋题 99% 或反序一致率推广为通用可靠性。

## 参评模型

| 模型 | 请求与部署 | 身份及说明 |
| --- | --- | --- |
| TypeSafe Jev | `https://api.typesafe.ai/v1/systemone`；默认请求 `jev-latest` | [TypeSafe System One](https://docs.typesafe.ai) 官方托管服务；记录实际返回版本，本轮入口不可用 |
| Microsoft Decision-1 | 用户提供的完整 Microsoft provider endpoint；请求 `Decision-1` | 探针及本轮有效结果实际返回 `microsoft-decision-1`；原生 Choice / Noul / Score，无文本提取兜底 |
| Qwen3.5-4B-Jev | 已有内网服务结果；`qwen35-4b-jev-v1` | 独立 Jev-like 模型，与 TypeSafe、Microsoft 无关；NF4 QLoRA＋标量决策头，不重新调用 |

Qwen 发布版本固定为 [`f5864f83`](https://huggingface.co/xuhaodev/Qwen3.5-4B-Jev/tree/f5864f83a4b09a242b5d7b8061c9c76eec4f3062)，基座为 [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B/tree/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a)。原评测前锁定最终模型，题集未参与该轮训练、校准或 checkpoint 选择；底座预训练及历史数据重叠未被全面排除。部署权重哈希未远程独立核验，详见 [provenance](results/qwen35-4b-provenance.json)。

## 快速开始

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env   # 仅在 .env 不存在时创建，然后填写凭据
```

**默认不调用模型**：运行 [benchmark.ipynb](benchmark.ipynb) 可离线查看保存的三模型结果；正式评测须显式启用 `RUN_LIVE` 或提供 CLI `--models`。不需要下载本地 ONNX 权重。

新的内部运行需使用不存在的结果路径：

```powershell
.\.venv\Scripts\python.exe -m jev_benchmark --models microsoft --output results\microsoft-new.json
.\.venv\Scripts\python.exe -m jev_benchmark --models jev --output results\jev-new.json
```

每个模型 100 次正式请求，可能计费。现有结果或检查点不会由 CLI 自动覆盖；本轮服务错误未自动重发。

重建外部数据必须核对历史清单，而不是重新采样：

```powershell
.\.venv\Scripts\python.exe -m jev_benchmark.external_data --output data\external-new.json --per-dataset 200 --reference-summary results\qwen35-4b-external-summary.json
```

如果固定 GitHub 原始源无法直连，可通过 `gh api` 下载固定 revision 的 `easy.jsonl`、`original.jsonl`、`hard.jsonl` 到同一目录，再传入 `--jevbench-source-dir`。公开数据下载显式禁用 Hugging Face token；可使用配置的 `HF_ENDPOINT` 公共镜像，最终仍须匹配历史清单哈希，不接受静默替换数据。

**以下是新的正式运行，不是失败运行的自动续跑。** 解除服务阻塞并确认新的调用额度后，选择一个模型、一个新目录：

```powershell
.\.venv\Scripts\python.exe -m jev_benchmark.external data\external-new.json --model microsoft --output results\external-microsoft-new --reference-summary results\qwen35-4b-external-summary.json --export-prefix results\microsoft-new-external
# Jev 使用 --model jev，并选择独立的新输出目录和导出前缀
```

外部每个模型 1,521 次正式请求。调用标记在发送前落盘，响应逐条保存；HTTP、网络、模型身份或结构化协议错误均停止，不自动重试或补跑。

限流或连接故障解除后，可**显式继续尚未尝试的题**到一个新目录，不重复发送此前任何题目：

```powershell
.\.venv\Scripts\python.exe -m jev_benchmark.external data\external-new.json --model microsoft --continue-from results\external-microsoft-interrupted --output results\external-microsoft-continue-new --min-interval 1.25 --reference-summary results\qwen35-4b-external-summary.json --export-prefix results\microsoft-continue-new-external
```

续跑核对清单、模型名、请求哈希、连续题号以及尝试标记。**始终选择最新快照，不要重新选择更早的快照**；本轮最终快照已覆盖全部题，会拒绝再次续跑。若存在“有标记但没有响应记录”的不确定请求，则拒绝续跑，避免误重发；原快照中的失败也不会被成功响应替换。`--min-interval` 控制请求开始间隔，不计入单题 HTTP 耗时。

如果已确认是孤立的网络重置或超时，可显式增加 `--continue-on-network-errors`：记录该题失败并移向**下一道**题，不重发；三个连续网络错误、任何 HTTP 错误或协议错误仍停止。默认不启用此行为。默认保持 HTTP keepalive；可显式使用 `--fresh-connections` 测试新连接，TLS 开销包含在单题耗时中。本轮部分续跑使用新连接，但未完全消除超时；保留的旧响应保持原有计时，不将混合传输条件当成纯推理速度。

离线重算本轮 Microsoft 的最终结果，不调用模型，仍返回非零状态以提示保留的请求失败：

```powershell
.\.venv\Scripts\python.exe -m jev_benchmark.external data\external-20261012.json --output results\external-microsoft-20261012-continued3 --report-only --export-prefix results\microsoft-20261012-continued3-external
```

离线重建对比，输出前缀必须不存在；以下显式将受阻 Jev 标为历史参考：

```powershell
.\.venv\Scripts\python.exe -m jev_benchmark.compare --internal results\local-jev.json results\microsoft-20261012.json results\qwen35-4b.json --external results\microsoft-20261012-continued3-external-summary.json results\qwen35-4b-external-summary.json --historical-model Jev-API qwen35-4b-jev-v1 --unavailable results\jev-20261012-status.json --output-prefix results\comparison-new
```

## 配置

| 变量 | 说明 | 使用场景 |
| --- | --- | --- |
| `JEV_API_KEY` | TypeSafe Jev 密钥 | `jev` |
| `JEV_ENDPOINT` | 默认 `https://api.typesafe.ai/v1/systemone`，必须 HTTPS | `jev` |
| `JEV_MODEL` | 默认 `jev-latest`；报表另记实际返回版本 | 可选 |
| `MICROSOFT_API_KEY` | Microsoft provider 密钥 | `microsoft` |
| `MICROSOFT_ENDPOINT` | **完整地址**：`https://func-meter-g4i4ocbcoq4pq.azurewebsites.net/providers/microsoft/v1/systemone`，不再拼接路径 | `microsoft` |
| `MICROSOFT_MODEL` | 默认 `Decision-1`，实际返回别名 `microsoft-decision-1` 已验证 | `microsoft` |
| `INTRANET_BASE_URL` | Qwen 自托管服务根地址，不含 `/v1/systemone` | 仅需重新调用 Qwen 时 |
| `INTRANET_API_KEY` | 自托管服务密钥 | `intranet` |
| `INTRANET_MODEL` | `qwen35-4b-jev-v1` | `intranet` |

系统环境变量优先于 `.env`，`.env.example` 不含真实密钥。HTTPS 不接受内嵌凭据、查询参数或片段；内网明文 HTTP 仅允许私有网段或本机 IP。错误不回显请求头、密钥或服务端错误正文。

## 题集与指标

题集：[data/implicit_intent.json](data/implicit_intent.json)，v1.0.0，随机猜测约 25%。

| 维度 | 分布 |
| --- | --- |
| 子集 | `marriage` 婚恋议题 love-001～050；`girlfriend-hint` 女友暗示 love-051～100 |
| 主题 | 婚恋含彩礼、婚房、双方父母、生育、家务等；暗示含约会、礼物、消息、点餐、醋意等，各 10 类 |
| 语义类型 | 反话与讽刺、借题表达、间接请求、试探确认、回避与保留，各 20 题 |
| 参考答案 | A 26、B 26、C 24、D 24；四项均为实质解释，无“信息不足”兜底项 |
| 对话 | 每题 6–8 次发言；末句不超过 35 字且无直接明示意图 |
| 上下文对照 | 10 组共 20 题末句相同、前文与参考含义不同；两题都答对才算整对通过 |

每题字段包括 `id`、`title`、`category`、`phenomenon`、`target_speaker`、`subset`、`state`、`options`、`reference`、`reason`。模型只接收 `state`、根级 `question` 与 `options`，其余字段及 `contrast_pairs` 仅用于评分。虚构人物风格不代表任何性别；不把明确拒绝反解为同意。

内部 JSON 保留题集版本、原始字节 SHA-256、UTC 日期、选择、概率、confidence、实际版本与耗时；每次调用后写检查点，全部成功才原子生成正式结果。加载和离线合并仅接受同题集及 LF / CRLF 等价哈希，按题号、元数据和模型身份核对，不把缺失选择伪装为答案。

## 代码与结果

| 路径 | 用途 |
| --- | --- |
| `jev_benchmark\__main__.py`、`evaluate.py` | 内部评测、检查点、同题合并与 HTML 报表 |
| `jev_benchmark\jev_api.py`、`microsoft.py` | 托管原生决策接口 |
| `jev_benchmark\external_data.py`、`external.py` | 固定外部清单、单次调用、统计与离线重算 |
| `jev_benchmark\compare.py` | 保存结果的离线比较，不调用模型 |
| `results\`、`benchmark.ipynb` | 发布结果和三模型展示；旧模型历史文件保留但不进入本次对比 |
| `data\external-*.json`、`results\external-*\` | 被 Git 忽略的外部原题、尝试标记和原始响应 |

## 测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

离线测试不调用真实模型，覆盖数据结构、协议、密钥保护、完整 endpoint、模型版本变化、失败检查点、续跑不重发、请求节流、孤立与系统性网络故障、哈希完整性、合并来源及默认不联网的 notebook。

## 局限与许可

内部题集是单一作者标注、未经独立人工复核的合成小样本，不是心理测量工具或通用排行榜；参考一致率不代表理解真实伴侣意图的能力。请勿用本题集训练后再报告成绩，修改题目需更新版本并重新评测。

代码采用 [MIT](LICENSE)，内部题集采用 [CC BY 4.0](data/LICENSE)。模型权重遵循各自许可。外部原始数据不随仓库分发；上游许可见完整报告。SST-5、STS-B 镜像未声明明确许可，不能把题目当作本仓库 CC BY 4.0 数据重新分发。
