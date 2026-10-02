# Qwen3.5-4B-Jev（NF4 QLoRA）测试报告

2026-10-02（本机时间；UTC 2026-10-01），最终锁定模型完成一次 **100题真实HTTP评测**：
**99/100参考一致率，同末句上下文对照10/10整对通过**。

- **模型下载：[xuhaodev/Qwen3.5-4B-Jev](https://huggingface.co/xuhaodev/Qwen3.5-4B-Jev)**
- **固定版本：[f5864f83a4b09a242b5d7b8061c9c76eec4f3062](https://huggingface.co/xuhaodev/Qwen3.5-4B-Jev/tree/f5864f83a4b09a242b5d7b8061c9c76eec4f3062)**
- **逐题原始结果：[qwen35-4b.json](qwen35-4b.json)**
- **发布与评测身份：[qwen35-4b-provenance.json](qwen35-4b-provenance.json)**
- [模型卡和独立加载器用法](https://huggingface.co/xuhaodev/Qwen3.5-4B-Jev#quick-start)

## 配置与隔离

| 项目 | 配置 |
| --- | --- |
| Benchmark代码 | [`d6308af55b0331f56558203606ec8f1057ca61a6`](https://github.com/haxudev/jev-benchmark/tree/d6308af55b0331f56558203606ec8f1057ca61a6) |
| 题集 | v1.0.0，100题Choice四选一 |
| 题集SHA256 | `cb42574c05a9198b7cb5ea91d59c278c7639f1a93ee3add20295a8c26f62298b` |
| 请求/响应模型名 | `qwen35-4b-jev-v1` |
| 基座 | [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B/tree/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a) |
| 训练 | NF4 4-bit QLoRA rank16/alpha32＋FP32决策头，6,000题、2轮、750次更新 |
| 选型/校准 | 独立Dev选择epoch2；独立Calibration拟合温度 |
| 运行环境 | NVIDIA GB10，Linux aarch64，PyTorch 2.13.0+cu130，Transformers 5.15.0 |
| 推理依赖 | PEFT 0.20.0，bitsandbytes 0.50.2，FLA 0.5.2，TypeSafe SDK 0.7.1 |
| 流程 | 原仓库 `run_benchmark`＋`IntranetClient`，loopback HTTP，顺序请求 |
| 模型输入 | 只有state、统一question与A–D选项；参考、解释和评分字段不发送 |
| 失败/重试 | 0/0 |

本轮训练未使用本题集，未用它选择checkpoint或校准。训练材料为历史审核语义合成题与程序规则，先做来源组隔离；对benchmark执行state-only原文hash排除。最终发布manifest在测试前锁定，测试后未修改权重/校准。本次未再对基座或其它checkpoint运行本题集。

公开发布时仅调整基座路径和模块导入，adapter、head、calibration逐字节保持一致；匿名下载校验通过，三种primitive的实模型冒烟输出与原锁定版本完全一致。该冒烟未重新运行本题集。

## 成绩

| 模型 | 总体 | 婚恋议题 | 女友暗示 | 同末句整对 |
| --- | --- | --- | --- | --- |
| 官方Jev（历史） | 100/100 | 50/50 | 50/50 | 10/10 |
| **Qwen3.5-4B-Jev** | **99/100** | **50/50** | **49/50** | **10/10** |
| Qwen3-1.7B-Jev v2（历史） | 78/100 | 40/50 | 38/50 | 4/10 |
| Qwen3.5-0.8B-Jev（历史） | 68/100 | 35/50 | 33/50 | 3/10 |

4B相对历史v2高21个百分点，多通过6组整对；不同底座/训练方案的比较不能证明微调本身带来21个百分点。

| 语义类型 | 结果 |
| --- | --- |
| 反话与讽刺 | 20/20 |
| 借题表达 | 20/20 |
| 间接请求 | 19/20 |
| 试探确认 | 20/20 |
| 回避与保留 | 20/20 |

20个主题中19个为5/5；“外表与购物”为4/5。

## 唯一不一致题

| 题号 | 标题 | 参考 | 模型 | 模型概率 |
| --- | --- | --- | --- | --- |
| love-073 | 快关门的试衣间 | D | B | A 0.01113 / B 0.51463 / C 0.00136 / D 0.47288 |

API confidence为0.45536。B与D接近；模型未被据此重新训练或校准。

## 延迟

| 指标 | 本次测量 |
| --- | --- |
| 平均 | 635.426 ms |
| P50 | 633.903 ms |
| P95 | 650.262 ms |

P95使用线性插值，与历史v2报告的nearest-rank定义略有区别。包含SDK创建、HTTP与解析；模型已经加载，单机顺序请求，不是冷启动或并发吞吐测量。模型体积、精度、推理引擎均不同，不能把跨模型延迟差单独归因为4-bit量化。

confidence采用归一化熵 `1-H(p)/log(K)`，与官方Jev数值不保证等价，也不等于正确概率。

## 复现

按 [固定版本模型卡](https://huggingface.co/xuhaodev/Qwen3.5-4B-Jev/blob/f5864f83a4b09a242b5d7b8061c9c76eec4f3062/README.md) 下载adapter、head、processor、校准与Python加载器，使用固定revision基座。通过兼容 `POST /v1/systemone` 的服务暴露模型，再配置：

```bash
export INTRANET_BASE_URL=http://127.0.0.1:18085
export INTRANET_API_KEY='<your-service-key>'
export INTRANET_MODEL=qwen35-4b-jev-v1
python -m jev_benchmark --models intranet
```

该命令会发起新一轮100次请求，并更新默认 `results/intranet.json`。本次归档文件 `qwen35-4b.json` 保留原始评测字节；查看它可使用notebook第2节，设置 `REPORT = "qwen35-4b.json"`，无需重新调用模型。

## 口径

这是100道中文婚恋多轮对话的参考一致率，不是通用准确率。题集为单一作者标注的合成诊断集；基座是否在预训练阶段接触过公开题目无法证明。服务4K预算也不表示通用长文质量已验证，本次只测试Choice。
