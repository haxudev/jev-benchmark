# Successful-request latency comparison

All values below are milliseconds. Only valid successful responses are included, regardless of correctness. Failures and waits are excluded.

## Internal 100 items

| 模型 | 成功样本数 | 均值 | p50 | p90 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Jev-API | 100 | 844.5 | 786.5 | 919.0 | 1128.6 | 1879.6 |
| Microsoft Decision | 100 | 1759.9 | 1608.1 | 2194.2 | 2303.3 | 6288.5 |
| qwen35-4b-jev-v1 | 100 | 635.4 | 633.9 | 646.2 | 650.3 | 666.1 |

## External 1,431 + 90 items

| 模型 | 成功样本数 | 均值 | p50 | p90 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| jev-1.13.0 | 1521 | 267.4 | 253.5 | 286.5 | 307.8 | 575.2 |
| microsoft-decision-1 | 1521 | 1274.1 | 1308.5 | 1730.1 | 1900.0 | 2406.4 |
| qwen35-4b-jev-v1 | 1521 | 539.8 | 422.2 | 未记录 | 652.5 | 未记录 |

Qwen external p90/p99 were not preserved; missing quantiles are not estimated from p50/p95. Deployments, dates and connection policies differ; these are HTTP client timings, not normalized hardware inference times.
