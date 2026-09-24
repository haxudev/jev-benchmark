# jev-benchmark

面向**语义决策模型**的中文评测集：100 道虚构伴侣多轮对话，检验模型能否结合上下文读出最后一句话的**言下之意**。

语义决策模型不生成自由文本，而是针对 `state` 与类型化问题直接返回结构化决策（选项与概率分布）。本题集全部为 **Choice 四选一**：模型接收对话、统一问题和 A–D 四个实质解释，返回所选项与概率；参考答案、解释与标签都不发送给模型。

## 成绩

| 模型 | 部署 | 参考一致率 | 婚恋议题 | 女友暗示 | 同末句对照（整对） |
|---|---|---|---|---|---|
| Jev-API（`jev-1.13.0`） | 官方托管 | **100.0%** | 100.0% | 100.0% | 10 / 10 |
| Qwen3.5-0.8B-Jev | 本地 ONNX · CPU | 68.0% | 70.0% | 66.0% | 3 / 10 |
| Qwen3-1.7B-Jev | 内网 · Jev-like | 未评测 | — | — | — |

题集 v1.0.0，2026-09-24 同题运行；随机猜测约 25%。两模型有 68 题选择相同且全部正确；本地模型最弱的是间接请求（11/20）与反话与讽刺（12/20）。Jev 平均 confidence 0.995，约 1.6 秒/题。逐题结果见 [results/local-jev.json](results/local-jev.json)，也可在 [benchmark.ipynb](benchmark.ipynb) 第 2 节直接查看排行榜与报表。

> 官方 Jev 在本题集上已达满分，本题集对它不再有区分度；目前更适合衡量本地 / 内网 Jev-like 模型与官方 Jev 的差距。

## 题集

[data/implicit_intent.json](data/implicit_intent.json)

| 维度 | 分布 |
|---|---|
| 子集 | `marriage` 婚恋议题 love-001～050：彩礼、婚房、双方父母、生育、家务等 10 个主题，最后发言者男女各半 |
| | `girlfriend-hint` 女友暗示 love-051～100：约会、礼物、消息回复、点餐、醋意等 10 个主题，最后发言者均为女友，男友在对话中的误判多作为干扰项 |
| 语义类型 | 反话与讽刺 · 借题表达 · 间接请求 · 试探确认 · 回避与保留，各 20 题 |
| 参考答案 | A 26 · B 26 · C 24 · D 24；四项均为实质解释，无“信息不足”兜底项 |
| 对话形态 | 每题 6–8 次发言；末句不超过 35 字且不含“我希望”“前提是”等明示句式 |
| 上下文对照 | 10 组共 20 题末句完全相同、前文与参考含义不同；两题都答对才算整对通过 |

每题字段：`id`、`title`、`category`（主题）、`phenomenon`（语义类型）、`target_speaker`、`subset`、`state`（背景与对话）、`options`、`reference`、`reason`。模型只接收 `state`、根级 `question` 与 `options`；其余字段和 `contrast_pairs` 仅用于评分。

正确项需多处前文证据支持，干扰项也是有一定合理性的解释。人物沟通风格为虚构设定，不代表任何性别；参考答案不以性别推断，也不把明确拒绝反解为同意。

## 参评模型

三类模型走同一个 Choice 接口：相同的 `state`、`question` 和 `options`，统一校验返回的选择与概率分布。

### 本地模型 · Qwen3.5-0.8B-Jev

| | |
|---|---|
| 权重 | [lokinfey/Qwen3_5_0.8B_jev](https://huggingface.co/lokinfey/Qwen3_5_0.8B_jev)，固定 revision `19409b2d`，Apache-2.0 |
| 来源 | Qwen3.5-0.8B 经 LoRA 在 typed-decisions-synth 上微调并导出 ONNX（[JevONNX](https://github.com/kinfey/JevONNX)）；社区模型，**不是**官方 Jev |
| 推理 | onnxruntime-genai CPU provider；读取首个生成位置的 A–D 字母 logits，仅在候选项间 softmax |
| 须知 | 官方导出面向 CUDA FP16，CPU 运行已在作者机器验证（约 1.8 秒/题），其他 CPU 不保证兼容；概率未经校准，不提供 confidence；训练提示为英文 |

### 官方模型 · Jev-API

| | |
|---|---|
| 服务 | [TypeSafe](https://docs.typesafe.ai) 的旗舰 System One 模型 Jev |
| 接口 | `POST https://api.typesafe.ai/v1/systemone`，Bearer 鉴权，`model: "jev-latest"`（[API 文档](https://docs.typesafe.ai/api)） |
| 协议 | Choice：`criteria` 传入 A–D，返回 `choice`、`probabilities`、`confidence`；结果记录实际版本号 |
| 须知 | 需要 `JEV_API_KEY`；全量评测 100 次请求，可能计费；超时 60 秒，不自动重试 |

### 内网模型 · Jev-like 自托管服务

| | |
|---|---|
| 参考模型 | [xuhaodev/Qwen3-1.7B-Jev](https://huggingface.co/xuhaodev/Qwen3-1.7B-Jev)（即 `football-decision-v2` 更名，权重不变），Apache-2.0 |
| 原理 | Qwen3-1.7B + LoRA + 标量决策头，逐候选打分后归一化，不做自回归生成；接口遵循 Jev 的 Choice / Score / Noul 约定 |
| 领域 | 中文足球决策数据训练；独立项目，与 TypeSafe 无关，**不是**官方 Jev，也未在伴侣对话语境训练 |
| 调用 | 部署为兼容 System One 的服务后，经 [typesafe-sdk](https://pypi.org/project/typesafe-sdk/) 0.6.0 的 `system_one` + `Choice` 调用，请求结构与官方 API 相同 |
| 传输 | HTTPS 不限主机；明文 HTTP 仅允许私有网段或本机 IP，且地址不得内嵌凭据 |
| 状态 | **尚未在本题集上评测**；报表中的模型名取自 `INTRANET_MODEL`，并记录服务实际返回的版本 |

## 快速开始

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m jev_benchmark.download   # 下载约 1.6 GB 权重到 model/ 并做 CPU 自检
.\.venv\Scripts\python.exe -m jev_benchmark            # 仅本地模型 → results/local.json
```

macOS / Linux 将 `.\.venv\Scripts\python.exe` 换成 `.venv/bin/python`。

对比远程模型：复制 `.env.example` 为 `.env` 并填写密钥，然后

```powershell
.\.venv\Scripts\python.exe -m jev_benchmark --models local jev intranet   # → results/local-jev-intranet.json
```

也可以在 [benchmark.ipynb](benchmark.ipynb) 中完成全部流程（VS Code 选择 `.venv` 解释器）：

1. **运行评测**：修改 `MODELS`（如 `["local", "jev"]`）后运行，结束即显示报表。
2. **查看结果**：不调用模型，汇总 `results/` 中与当前题集一致的结果为排行榜，并展开总榜、子集、语义类型、主题、对照题、模型间一致率、分歧题与逐题详情。克隆后可直接查看仓库自带的结果。
3. **附录**：本地模型的 noul / choice / score 三种决策原语演示。

## 配置

| 变量 | 说明 | 何时需要 |
|---|---|---|
| `JEV_API_KEY` | 官方 API 密钥 | `jev` |
| `JEV_ENDPOINT` | 默认 `https://api.typesafe.ai/v1/systemone`，须为 HTTPS | 可选 |
| `INTRANET_BASE_URL` | 内网服务根地址，如 `http://192.168.1.10:8082`（不含 `/v1/systemone`） | `intranet` |
| `INTRANET_API_KEY` | 内网服务密钥 | `intranet` |
| `INTRANET_MODEL` | 服务端模型名，同时作为报表中的模型名 | `intranet` |

系统环境变量优先于 `.env`。`.env` 已被 Git 忽略；错误信息不回显密钥、请求头或原始响应。

## 指标与结果文件

- **参考一致率**：模型选择与编写者参考相同的比例，另按子集、语义类型、主题分组。
- **同末句对照整对通过率**：一对中两题都与各自参考一致才算通过，分母为 10 对。
- **模型间一致率**：两个模型选择相同的比例；可能一起答错，不等于正确率。

结果 JSON 记录题集版本与 SHA-256、UTC 时间，以及每题各模型的选择、概率、confidence、实际版本和耗时。运行中每次调用后写入 `*.partial.json`；失败即报错并保留已完成部分，不补假结果；全部成功后原子替换为正式结果。题集变动后，旧结果因哈希不符而拒绝渲染。

## 目录结构

```text
jev-benchmark/
├── data/implicit_intent.json   # 题集
├── results/                    # 评测结果，文件名即模型组合
├── jev_benchmark/
│   ├── __main__.py             # 命令行入口
│   ├── evaluate.py             # 运行、统计与 HTML 报表
│   ├── local_model.py          # 本地 ONNX 模型
│   ├── jev_api.py              # Jev 官方 API
│   ├── intranet.py             # 内网模型（TypeSafe SDK）
│   └── download.py             # 下载本地权重
├── tests/                      # 离线测试：不加载模型、不联网
├── benchmark.ipynb
└── .env.example
```

## 测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

覆盖题集结构与均衡、三类模型的协议适配、密钥不外泄、传输限制、统计口径、失败检查点与 HTML 转义。

## 局限

- 合成、单一作者标注、未经独立人工复核的小规模诊断集；间接表达本身存在歧义。不是心理测量工具，也不是通用排行榜。
- 成绩只反映与编写者参考的一致程度，不代表理解真实伴侣意图的能力，也不构成彩礼、产权、生育等事项的建议。
- 请勿用本题集训练后再报告成绩；修改题目请更新版本并重新评测。

## 许可

代码采用 [MIT](LICENSE)，题集采用 [CC BY 4.0](data/LICENSE)。本地模型权重不随仓库分发，遵循其自身的 Apache-2.0 许可。
