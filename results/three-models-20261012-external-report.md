# External model comparison

Frozen manifest: `fbb21679cd930b0397a3adcc20d408e422cb816596f0921673ef5602621d4d02`.
1431 primary items + 90 option reversals per model.

Saved results only. Model dates and deployments differ; latency is not normalized hardware performance.
Models without a saved summary are not evaluated here; missing results are not assigned a score.

**Refresh status: partial**. Only fully valid tasks receive benchmark scores below; diagnostic JSON retains incomplete-run metrics.

| Model | UTC completed | Recorded | Valid | Status | Source |
| --- | --- | ---: | ---: | --- | --- |
| microsoft-decision-1 | 2026-10-12T09:15:25.849358+00:00 | 93 | 92 | failed | microsoft-20261012-external-summary.json |
| qwen35-4b-jev-v1 | 2026-10-02T03:09:27.174493+00:00 | 1521 | 1521 | complete | qwen35-4b-external-summary.json |
| Jev-API | Not run | 0 | 0 | blocked: HTTP 451 from the official endpoint | jev-20261012-status.json |

## Task metrics

| Task | Model | N | Attempted | Valid | Status | Accuracy | Brier (sum) | NLL | ECE | MAE | Spearman | p50 / p95 (s) |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ag_news | microsoft-decision-1 | 200 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |
| ag_news | qwen35-4b-jev-v1 | 200 | 200 | 200 | complete | 0.8250 | 0.3091 | 1.0979 | 0.1458 | N/A | N/A | 0.3953 / 0.4277 |
| anli | microsoft-decision-1 | 200 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |
| anli | qwen35-4b-jev-v1 | 200 | 200 | 200 | complete | 0.4800 | 0.9142 | 2.6499 | 0.4371 | N/A | N/A | 0.4202 / 0.4403 |
| belebele-zho_Hans | microsoft-decision-1 | 200 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |
| belebele-zho_Hans | qwen35-4b-jev-v1 | 200 | 200 | 200 | complete | 0.8450 | 0.2567 | 0.5565 | 0.0774 | N/A | N/A | 0.5478 / 0.6023 |
| boolq | microsoft-decision-1 | 200 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |
| boolq | qwen35-4b-jev-v1 | 200 | 200 | 200 | complete | 0.8300 | 0.2321 | 0.3899 | 0.0964 | N/A | N/A | 0.2254 / 0.3421 |
| jevbench-easy | microsoft-decision-1 | 48 | 48 | 48 | complete | 1.0000 | 0.0000 | 0.0025 | 0.0025 | N/A | N/A | 0.5105 / 1.0765 |
| jevbench-easy | qwen35-4b-jev-v1 | 48 | 48 | 48 | complete | 1.0000 | 0.0007 | 0.0043 | 0.0041 | N/A | N/A | 0.4437 / 0.4905 |
| jevbench-hard | microsoft-decision-1 | 111 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |
| jevbench-hard | qwen35-4b-jev-v1 | 111 | 111 | 111 | complete | 0.5495 | 0.5508 | 0.9774 | 0.2017 | 0.6427 | 0.4629 | 0.8021 / 5.0367 |
| jevbench-original | microsoft-decision-1 | 72 | 45 | 44 | incomplete | N/A | N/A | N/A | N/A | N/A | N/A | 0.4777 / 0.6611 |
| jevbench-original | qwen35-4b-jev-v1 | 72 | 72 | 72 | complete | 0.9444 | 0.0809 | 0.1363 | 0.0383 | 0.0090 | 0.9608 | 0.3571 / 0.5903 |
| sst5 | microsoft-decision-1 | 200 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |
| sst5 | qwen35-4b-jev-v1 | 200 | 200 | 200 | complete | 0.4250 | 0.9501 | 2.4533 | 0.4462 | 0.6785 | 0.7223 | 0.4212 / 0.4394 |
| stsb | microsoft-decision-1 | 200 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |
| stsb | qwen35-4b-jev-v1 | 200 | 200 | 200 | complete | N/A | N/A | N/A | N/A | 0.6004 | 0.8776 | 0.5453 / 0.6017 |

## Option reversals

Rates use all configured pairs; invalid or unattempted pairs do not count as agreement.

| Task | Model | Valid / total pairs | Same choice | Both correct |
| --- | --- | ---: | ---: | ---: |
| ag_news | microsoft-decision-1 | 0/20 | N/A | N/A |
| anli | microsoft-decision-1 | 0/20 | N/A | N/A |
| belebele-zho_Hans | microsoft-decision-1 | 0/20 | N/A | N/A |
| jevbench-easy | microsoft-decision-1 | 0/10 | N/A | N/A |
| jevbench-hard | microsoft-decision-1 | 0/10 | N/A | N/A |
| jevbench-original | microsoft-decision-1 | 0/10 | N/A | N/A |
| ag_news | qwen35-4b-jev-v1 | 20/20 | 1.0000 | 0.8500 |
| anli | qwen35-4b-jev-v1 | 20/20 | 1.0000 | 0.6000 |
| belebele-zho_Hans | qwen35-4b-jev-v1 | 20/20 | 1.0000 | 0.9000 |
| jevbench-easy | qwen35-4b-jev-v1 | 10/10 | 1.0000 | 1.0000 |
| jevbench-hard | qwen35-4b-jev-v1 | 10/10 | 1.0000 | 0.3000 |
| jevbench-original | qwen35-4b-jev-v1 | 10/10 | 1.0000 | 0.8000 |
