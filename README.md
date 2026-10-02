# jev-benchmark

面向**语义决策模型**的中文评测集：100 道婚恋送命题多轮对话，检验模型能否结合上下文读出**真实意图**。

语义决策模型不生成自由文本，而是针对 `state` 与类型化问题直接返回结构化决策（选项与概率分布）。本题集全部为 **Choice 四选一**：模型接收对话、统一问题和 A–D 四个实质解释，返回所选项与概率；参考答案、解释与标签都不发送给模型。

## 成绩

| 模型                      | 部署             | 参考一致率       | 婚恋议题 | 女友暗示 | 同末句对照（整对） |
| ------------------------- | ---------------- | ---------------- | -------- | -------- | ------------------ |
| Jev-API（`jev-1.13.0`） | 官方托管         | **100.0%** | 100.0%   | 100.0%   | 10 / 10            |
| [Qwen3.5-4B-Jev](https://huggingface.co/xuhaodev/Qwen3.5-4B-Jev) | 本地 · NF4 4-bit · GB10 | **99.0%** | **100.0%** | **98.0%** | **10 / 10** |
| Qwen3-1.7B-Jev（v2）      | 内网 · Jev-like · GB10 | 78.0%       | 80.0%    | 76.0%    | 4 / 10             |
| Qwen3.5-0.8B-Jev          | 本地 ONNX · CPU | 68.0%            | 70.0%    | 66.0%    | 3 / 10             |

题集 v1.0.0；随机猜测约25%。**2026-10-02新增 Qwen3.5-4B-Jev：99/100，同末句对照10/10**，平均约635 ms/题（已加载模型、本机HTTP、顺序调用）。测试前锁定最终模型，题集未参与该轮训练、校准或checkpoint选择；完成一次100题测试后未调整模型。

**[4B测试报告](results/qwen35-4b-report.md)** · **[逐题原始结果](results/qwen35-4b.json)** · **[Hugging Face模型](https://huggingface.co/xuhaodev/Qwen3.5-4B-Jev/tree/f5864f83a4b09a242b5d7b8061c9c76eec4f3062)**。

其余成绩来自2026-09-24已保存结果。v2指 `football-decision-v2`，发布名 `Qwen3-1.7B-Jev`，成绩78%、整对4/10；4B比它高21个百分点。不同底座、训练与推理路径的比较不能单独归因于微调。

历史资料：[v2测试报告](results/v2-report.md) · [v2原始结果](results/intranet.json) · [0.8B / 官方Jev](results/local-jev.json)。在 [benchmark.ipynb](benchmark.ipynb) 第2节重新运行查看结果单元格即可刷新四模型排行榜，设置 `REPORT = "qwen35-4b.json"` 查看4B报表，无需重新请求模型。

> 官方 Jev 在本题集上已达满分，本题集对它不再有区分度；目前更适合衡量本地 / 内网 Jev-like 模型与官方 Jev 的差距。

## 题集

[data/implicit_intent.json](data/implicit_intent.json)

| 维度       | 分布                                                                                                                                         |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 子集       | `marriage` 婚恋议题 love-001～050：彩礼、婚房、双方父母、生育、家务等 10 个主题，最后发言者男女各半                                        |
|            | `girlfriend-hint` 女友暗示 love-051～100：约会、礼物、消息回复、点餐、醋意等 10 个主题，最后发言者均为女友，男友在对话中的误判多作为干扰项 |
| 语义类型   | 反话与讽刺 · 借题表达 · 间接请求 · 试探确认 · 回避与保留，各 20 题                                                                       |
| 参考答案   | A 26 · B 26 · C 24 · D 24；四项均为实质解释，无“信息不足”兜底项                                                                         |
| 对话形态   | 每题 6–8 次发言；末句不超过 35 字且不含“我希望”“前提是”等明示句式                                                                       |
| 上下文对照 | 10 组共 20 题末句完全相同、前文与参考含义不同；两题都答对才算整对通过                                                                        |

每题字段：`id`、`title`、`category`（主题）、`phenomenon`（语义类型）、`target_speaker`、`subset`、`state`（背景与对话）、`options`、`reference`、`reason`。模型只接收 `state`、根级 `question` 与 `options`；其余字段和 `contrast_pairs` 仅用于评分。

正确项需多处前文证据支持，干扰项也是有一定合理性的解释。人物沟通风格为虚构设定，不代表任何性别；参考答案不以性别推断，也不把明确拒绝反解为同意。

## 参评模型

### Qwen3.5-4B-Jev · NF4 4-bit

| 项目 | 配置 |
| --- | --- |
| 模型 | [xuhaodev/Qwen3.5-4B-Jev](https://huggingface.co/xuhaodev/Qwen3.5-4B-Jev) |
| 固定发布版本 | [`f5864f83`](https://huggingface.co/xuhaodev/Qwen3.5-4B-Jev/tree/f5864f83a4b09a242b5d7b8061c9c76eec4f3062) |
| 基座 | [Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B/tree/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a) |
| 微调 | NF4 QLoRA rank16＋FP32标量决策头；6,000题、2轮、750次更新 |
| 推理 | state＋问题＋完整criteria＋当前候选，prefill-only打分；独立温度校准，无文本生成 |
| API模型名 | `qwen35-4b-jev-v1`；发布仓库名为 `Qwen3.5-4B-Jev` |
| 协议 / 上下文 | Choice / Score / Noul；每候选4K输入预算，本评测仅测试Choice |
| 成绩 | **99/100，婚恋50/50，女友暗示49/50，整对10/10** |

发布包包含adapter、决策头、processor、校准和独立Python加载器，需另下载固定revision的官方基座。加载方法见 [模型卡](https://huggingface.co/xuhaodev/Qwen3.5-4B-Jev#quick-start)；这是独立Jev-like模型。

所有参评模型走同一个 Choice 接口：相同的 `state`、`question` 和 `options`，统一校验返回的选择与概率分布。

### 本地模型 · Qwen3.5-0.8B-Jev

|      |                                                                                                                                                  |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 权重 | [lokinfey/Qwen3_5_0.8B_jev](https://huggingface.co/lokinfey/Qwen3_5_0.8B_jev)，固定 revision `19409b2d`，Apache-2.0                             |
| 来源 | Qwen3.5-0.8B 经 LoRA 在 typed-decisions-synth 上微调并导出 ONNX（[JevONNX](https://github.com/kinfey/JevONNX)）；社区模型，**不是**官方 Jev |
| 推理 | onnxruntime-genai CPU provider；读取首个生成位置的 A–D 字母 logits，仅在候选项间 softmax                                                        |
| 须知 | 官方导出面向 CUDA FP16，CPU 运行已在作者机器验证（约 1.8 秒/题），其他 CPU 不保证兼容；概率未经校准，不提供 confidence；训练提示为英文           |

### 官方模型 · Jev-API

|      |                                                                                                                                |
| ---- | ------------------------------------------------------------------------------------------------------------------------------ |
| 服务 | [TypeSafe](https://docs.typesafe.ai) 的旗舰 System One 模型 Jev                                                                 |
| 接口 | `POST https://api.typesafe.ai/v1/systemone`，Bearer 鉴权，`model: "jev-latest"`（[API 文档](https://docs.typesafe.ai/api)） |
| 协议 | Choice：`criteria` 传入 A–D，返回 `choice`、`probabilities`、`confidence`；结果记录实际版本号                         |
| 须知 | 需要`JEV_API_KEY`；全量评测 100 次请求，可能计费；超时 60 秒，不自动重试                                                     |

### 内网模型 · Jev-like 自托管服务

|          |                                                                                                                                                            |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 参考模型 | [xuhaodev/Qwen3-1.7B-Jev](https://huggingface.co/xuhaodev/Qwen3-1.7B-Jev)，Apache-2.0                                                                       |
| 本次版本 | `football-decision-v2` epoch-2，发布后更名为 `Qwen3-1.7B-Jev`；adapter、决策头和校准文件哈希已与原 v2 release 核对一致，见 [v2 报告](results/v2-report.md) |
| 原理     | Qwen3-1.7B + LoRA + 标量决策头，逐候选打分后归一化，不做自回归生成；接口遵循 Jev 的 Choice / Score / Noul 约定                                             |
| 领域     | 中文足球决策数据训练；独立项目，与 TypeSafe 无关，**不是**官方 Jev，也未在伴侣对话语境训练                                                           |
| 调用     | 部署为兼容 System One 的服务后，经[typesafe-sdk](https://pypi.org/project/typesafe-sdk/) 0.6.0 的 `system_one` + `Choice` 调用，请求结构与官方 API 相同 |
| 传输     | HTTPS 不限主机；明文 HTTP 仅允许私有网段或本机 IP，且地址不得内嵌凭据                                                                                      |
| 状态     | **已完成 100 题：78.0%，对照整对 4/10**；请求与实际响应模型名均为 `Qwen3-1.7B-Jev`，详见 [原始结果](results/intranet.json) |

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

仅运行 v2：在 `.env` 中填写 `INTRANET_BASE_URL`、`INTRANET_API_KEY`，并设置 `INTRANET_MODEL=Qwen3-1.7B-Jev`，然后运行：

```bash
.venv/bin/python -m jev_benchmark --models intranet   # 100 次请求 → results/intranet.json
```

服务需要预先部署 v2 权重；再次运行会在成功后替换同名结果。只测内网服务不需要下载本地 ONNX 权重。

也可以在 [benchmark.ipynb](benchmark.ipynb) 中完成全部流程（VS Code 选择 `.venv` 解释器）：

1. **运行评测**：修改 `MODELS`（如 `["local", "jev"]`）后运行，结束即显示报表。
2. **查看结果**：不调用模型，汇总 `results/` 中与当前题集一致的结果为排行榜，并展开总榜、子集、语义类型、主题、对照题、模型间一致率、分歧题与逐题详情。克隆后可直接查看仓库自带的结果。
3. **附录**：本地模型的 noul / choice / score 三种决策原语演示。

## 配置

| 变量                  | 说明                                                                     | 何时需要     |
| --------------------- | ------------------------------------------------------------------------ | ------------ |
| `JEV_API_KEY`       | 官方 API 密钥                                                            | `jev`      |
| `JEV_ENDPOINT`      | 默认`https://api.typesafe.ai/v1/systemone`，须为 HTTPS                 | 可选         |
| `INTRANET_BASE_URL` | 内网服务根地址，如`http://192.168.1.10:8082`（不含 `/v1/systemone`） | `intranet` |
| `INTRANET_API_KEY`  | 内网服务密钥                                                             | `intranet` |
| `INTRANET_MODEL`    | 服务端模型名，同时作为报表中的模型名                                     | `intranet` |

系统环境变量优先于 `.env`。`.env` 已被 Git 忽略；错误信息不回显密钥、请求头或原始响应。

## 指标与结果文件

- **参考一致率**：模型选择与编写者参考相同的比例，另按子集、语义类型、主题分组。
- **同末句对照整对通过率**：一对中两题都与各自参考一致才算通过，分母为 10 对。
- **模型间一致率**：两个模型选择相同的比例；可能一起答错，不等于正确率。

结果 JSON 记录题集版本与 SHA-256、UTC 时间，以及每题各模型的选择、概率、confidence、实际版本和耗时。运行中每次调用后写入 `*.partial.json`；失败即报错并保留已完成部分，不补假结果；全部成功后原子替换为正式结果。加载器保留原始字节哈希，兼容 Git 在 Windows / Linux 间的 CRLF / LF 换行转换；题集内容变动后，旧结果因哈希不符而不会被加载到报表。

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
