# External model comparison

Frozen manifest: `fbb21679cd930b0397a3adcc20d408e422cb816596f0921673ef5602621d4d02`.
1431 primary items + 90 option reversals per model.

Saved results only. Model dates and deployments differ; latency is not normalized hardware performance.
Models without a saved summary are not evaluated here; missing results are not assigned a score.

**Refresh status: partial**. Only fully attempted tasks receive benchmark scores below; API failures count as incorrect, and diagnostic JSON retains incomplete-run metrics.

Probability metrics use the reported vectors without renormalization. Jev 1.13 reports hundredths; its zero-rounding can inflate epsilon-floored NLL relative to full-precision providers. Ordinal metrics use each API's native Score.

| Model | UTC completed | Recorded | Valid | All items attempted | Status | Source |
| --- | --- | ---: | ---: | --- | --- | --- |
| jev-1.13.0 | 2026-10-12T11:44:14.470632+00:00 | 1521 | 1521 | True | complete | jev-20261012-continued-external-summary.json |
| microsoft-decision-1 | 2026-10-12T10:36:32.695539+00:00 | 1521 | 1505 | True | failed | microsoft-20261012-continued3-external-summary.json |
| qwen35-4b-jev-v1 | 2026-10-02T03:09:27.174493+00:00 | 1521 | 1521 | True | complete | qwen35-4b-external-summary.json |

## Task metrics

| Task | Model | N | Attempted | Valid | Status | Accuracy | Brier (sum) | NLL | ECE | MAE | Spearman | p50 / p95 (s) |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ag_news | jev-1.13.0 | 200 | 200 | 200 | complete | 0.8700 | 0.2083 | 1.9139 | 0.0876 | N/A | N/A | 0.2506 / 0.2930 |
| ag_news | microsoft-decision-1 | 200 | 200 | 199 | failed | 0.8900 | 0.1834 | 0.3669 | 0.0584 | N/A | N/A | 1.0059 / 1.6093 |
| ag_news | qwen35-4b-jev-v1 | 200 | 200 | 200 | complete | 0.8250 | 0.3091 | 1.0979 | 0.1458 | N/A | N/A | 0.3953 / 0.4277 |
| anli | jev-1.13.0 | 200 | 200 | 200 | complete | 0.7150 | 0.4234 | 1.4919 | 0.1340 | N/A | N/A | 0.2589 / 0.3277 |
| anli | microsoft-decision-1 | 200 | 200 | 199 | failed | 0.6300 | 0.5046 | 0.8790 | 0.1615 | N/A | N/A | 1.3911 / 1.9381 |
| anli | qwen35-4b-jev-v1 | 200 | 200 | 200 | complete | 0.4800 | 0.9142 | 2.6499 | 0.4371 | N/A | N/A | 0.4202 / 0.4403 |
| belebele-zho_Hans | jev-1.13.0 | 200 | 200 | 200 | complete | 0.9400 | 0.0926 | 0.4903 | 0.0338 | N/A | N/A | 0.2517 / 0.3056 |
| belebele-zho_Hans | microsoft-decision-1 | 200 | 200 | 193 | failed | 0.9400 | 0.0308 | 0.0806 | 0.0497 | N/A | N/A | 1.3905 / 1.9406 |
| belebele-zho_Hans | qwen35-4b-jev-v1 | 200 | 200 | 200 | complete | 0.8450 | 0.2567 | 0.5565 | 0.0774 | N/A | N/A | 0.5478 / 0.6023 |
| boolq | jev-1.13.0 | 200 | 200 | 200 | complete | 0.9000 | 0.1572 | 0.2665 | 0.0250 | N/A | N/A | 0.2549 / 0.3041 |
| boolq | microsoft-decision-1 | 200 | 200 | 199 | failed | 0.8600 | 0.1915 | 0.3160 | 0.0731 | N/A | N/A | 1.3281 / 1.9286 |
| boolq | qwen35-4b-jev-v1 | 200 | 200 | 200 | complete | 0.8300 | 0.2321 | 0.3899 | 0.0964 | N/A | N/A | 0.2254 / 0.3421 |
| jevbench-easy | jev-1.13.0 | 48 | 48 | 48 | complete | 1.0000 | 0.0002 | 0.0044 | 0.0044 | N/A | N/A | 0.2529 / 0.5869 |
| jevbench-easy | microsoft-decision-1 | 48 | 48 | 48 | complete | 1.0000 | 0.0000 | 0.0025 | 0.0025 | N/A | N/A | 0.5105 / 1.0765 |
| jevbench-easy | qwen35-4b-jev-v1 | 48 | 48 | 48 | complete | 1.0000 | 0.0007 | 0.0043 | 0.0041 | N/A | N/A | 0.4437 / 0.4905 |
| jevbench-hard | jev-1.13.0 | 111 | 111 | 111 | complete | 0.7207 | 0.3517 | 0.5967 | 0.0847 | 0.3767 | 0.7715 | 0.2487 / 0.2962 |
| jevbench-hard | microsoft-decision-1 | 111 | 111 | 111 | complete | 0.8198 | 0.2609 | 0.4769 | 0.0408 | 0.4366 | 0.6172 | 0.5486 / 1.0813 |
| jevbench-hard | qwen35-4b-jev-v1 | 111 | 111 | 111 | complete | 0.5495 | 0.5508 | 0.9774 | 0.2017 | 0.6427 | 0.4629 | 0.8021 / 5.0367 |
| jevbench-original | jev-1.13.0 | 72 | 72 | 72 | complete | 0.9861 | 0.0269 | 0.0562 | 0.0453 | 0.0033 | 0.9852 | 0.2514 / 0.3688 |
| jevbench-original | microsoft-decision-1 | 72 | 72 | 71 | failed | 0.9861 | 0.0015 | 0.0120 | 0.0116 | 0.0014 | 0.9608 | 0.5177 / 1.0922 |
| jevbench-original | qwen35-4b-jev-v1 | 72 | 72 | 72 | complete | 0.9444 | 0.0809 | 0.1363 | 0.0383 | 0.0090 | 0.9608 | 0.3571 / 0.5903 |
| sst5 | jev-1.13.0 | 200 | 200 | 200 | complete | 0.5200 | 0.7219 | 3.0408 | 0.2502 | 0.5978 | 0.7996 | 0.2569 / 0.3022 |
| sst5 | microsoft-decision-1 | 200 | 200 | 197 | failed | 0.5250 | 0.5923 | 1.0534 | 0.1023 | 0.5505 | 0.8376 | 1.3911 / 1.9010 |
| sst5 | qwen35-4b-jev-v1 | 200 | 200 | 200 | complete | 0.4250 | 0.9501 | 2.4533 | 0.4462 | 0.6785 | 0.7223 | 0.4212 / 0.4394 |
| stsb | jev-1.13.0 | 200 | 200 | 200 | complete | N/A | N/A | N/A | N/A | 0.5055 | 0.9015 | 0.2533 / 0.3226 |
| stsb | microsoft-decision-1 | 200 | 200 | 198 | failed | N/A | N/A | N/A | N/A | 0.4501 | 0.9291 | 1.3840 / 1.8924 |
| stsb | qwen35-4b-jev-v1 | 200 | 200 | 200 | complete | N/A | N/A | N/A | N/A | 0.6004 | 0.8776 | 0.5453 / 0.6017 |

## Option reversals

Rates use all configured pairs; invalid or unattempted pairs do not count as agreement.

| Task | Model | Valid / total pairs | Same choice | Both correct |
| --- | --- | ---: | ---: | ---: |
| ag_news | jev-1.13.0 | 20/20 | 1.0000 | 0.8500 |
| anli | jev-1.13.0 | 20/20 | 0.9500 | 0.7500 |
| belebele-zho_Hans | jev-1.13.0 | 20/20 | 1.0000 | 0.9000 |
| jevbench-easy | jev-1.13.0 | 10/10 | 1.0000 | 1.0000 |
| jevbench-hard | jev-1.13.0 | 10/10 | 1.0000 | 0.5000 |
| jevbench-original | jev-1.13.0 | 10/10 | 1.0000 | 1.0000 |
| ag_news | microsoft-decision-1 | 20/20 | 1.0000 | 0.9000 |
| anli | microsoft-decision-1 | 20/20 | 1.0000 | 0.7500 |
| belebele-zho_Hans | microsoft-decision-1 | 20/20 | 1.0000 | 1.0000 |
| jevbench-easy | microsoft-decision-1 | 10/10 | 1.0000 | 1.0000 |
| jevbench-hard | microsoft-decision-1 | 10/10 | 1.0000 | 0.8000 |
| jevbench-original | microsoft-decision-1 | 10/10 | 1.0000 | 1.0000 |
| ag_news | qwen35-4b-jev-v1 | 20/20 | 1.0000 | 0.8500 |
| anli | qwen35-4b-jev-v1 | 20/20 | 1.0000 | 0.6000 |
| belebele-zho_Hans | qwen35-4b-jev-v1 | 20/20 | 1.0000 | 0.9000 |
| jevbench-easy | qwen35-4b-jev-v1 | 10/10 | 1.0000 | 1.0000 |
| jevbench-hard | qwen35-4b-jev-v1 | 10/10 | 1.0000 | 0.3000 |
| jevbench-original | qwen35-4b-jev-v1 | 10/10 | 1.0000 | 0.8000 |
