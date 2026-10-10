# Qwen3.5-4B-Jev External Evaluation

Model: `qwen35-4b-jev-v1`. Manifest SHA-256: `fbb21679cd930b0397a3adcc20d408e422cb816596f0921673ef5602621d4d02`.

Requests recorded: 1521/1521.

| Suite | N | Valid | Accuracy | Brier (sum) | NLL | ECE | MAE | Spearman | p50 / p95 (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ag_news | 200 | 200 | 0.8250 | 0.3091 | 1.0979 | 0.1458 | N/A | N/A | 0.3953 / 0.4277 |
| anli | 200 | 200 | 0.4800 | 0.9142 | 2.6499 | 0.4371 | N/A | N/A | 0.4202 / 0.4403 |
| belebele-zho_Hans | 200 | 200 | 0.8450 | 0.2567 | 0.5565 | 0.0774 | N/A | N/A | 0.5478 / 0.6023 |
| boolq | 200 | 200 | 0.8300 | 0.2321 | 0.3899 | 0.0964 | N/A | N/A | 0.2254 / 0.3421 |
| jevbench-easy | 48 | 48 | 1.0000 | 0.0007 | 0.0043 | 0.0041 | N/A | N/A | 0.4437 / 0.4905 |
| jevbench-hard | 111 | 111 | 0.5495 | 0.5508 | 0.9774 | 0.2017 | 0.6427 | 0.4629 | 0.8021 / 5.0367 |
| jevbench-original | 72 | 72 | 0.9444 | 0.0809 | 0.1363 | 0.0383 | 0.0090 | 0.9608 | 0.3571 / 0.5903 |
| sst5 | 200 | 200 | 0.4250 | 0.9501 | 2.4533 | 0.4462 | 0.6785 | 0.7223 | 0.4212 / 0.4394 |
| stsb | 200 | 200 | N/A | N/A | N/A | N/A | 0.6004 | 0.8776 | 0.5453 / 0.6017 |

## Interpretation

- JevBench results cover only the pinned, published public cohorts, not the full leaderboard.
- Accuracy counts failures and unattempted items as incorrect; probability metrics use valid vectors only.
- Brier uses the multiclass sum convention. NLL floors probabilities at 1e-15 and reports zero-mass rows.
- ECE uses top-label probability and reference agreement, not the model's entropy-based confidence.
- Score tasks retain expected-level MAE and Spearman; continuous STS-B targets have no fabricated gold distribution.
- Risk/coverage curves are descriptive; no threshold or temperature is fitted on these test cases.
- Accuracy intervals resample whole scenario groups (1,000 bootstrap draws).
- Latency is serial client wall time with a loaded self-hosted model, not normalized GPU throughput.
- No model tuning, retry, hidden probability normalization, or paid official Jev calls.
- Zero-shot means no benchmark-directed tuning in this run; pretraining and historical training overlap are not ruled out.
- Actual model identity was checked on every response; deployed weight hashes were not independently inspected.

## Failures

No failed or invalid primary responses.

## Option Reversal

| Suite | Valid pairs | Same choice | Both correct |
| --- | ---: | ---: | ---: |
| ag_news | 20 | 1.0000 | 0.8500 |
| anli | 20 | 1.0000 | 0.6000 |
| belebele-zho_Hans | 20 | 1.0000 | 0.9000 |
| jevbench-easy | 10 | 1.0000 | 1.0000 |
| jevbench-hard | 10 | 1.0000 | 0.3000 |
| jevbench-original | 10 | 1.0000 | 0.8000 |

## High-Probability Decisions

Descriptive p_max >= 0.9 slice; these are not fitted deployment thresholds.

| Suite | Accepted | Coverage | Error rate |
| --- | ---: | ---: | ---: |
| ag_news | 184 | 0.9200 | 0.1522 |
| anli | 133 | 0.6650 | 0.5263 |
| belebele-zho_Hans | 127 | 0.6350 | 0.0472 |
| boolq | 151 | 0.7550 | 0.0530 |
| jevbench-easy | 47 | 0.9792 | 0.0000 |
| jevbench-hard | 37 | 0.3333 | 0.1622 |
| jevbench-original | 62 | 0.8611 | 0.0161 |
| sst5 | 129 | 0.6450 | 0.5194 |

## Systems

```json
{
  "actual_models": [
    "qwen35-4b-jev-v1"
  ],
  "valid_responses": 1521,
  "mean_seconds": 0.5397951357660246,
  "p50_seconds": 0.4221778999999515,
  "p95_seconds": 0.6525077999976929,
  "sum_request_seconds": 821.0284015001234,
  "reported_input_tokens": 1807251,
  "reported_output_tokens": 0,
  "cost_usd": null,
  "cost_basis": "self-hosted; GPU cost and power were not measured"
}
```

## Data Revisions

| Repository | Revision | File | Source license |
| --- | --- | --- | --- |
| fstandhartinger/jevbench | bb05a335bc809e61b20c0f745d25499a82b326fc | datasets/public/easy.jsonl | MIT |
| fstandhartinger/jevbench | bb05a335bc809e61b20c0f745d25499a82b326fc | datasets/public/original.jsonl | MIT |
| fstandhartinger/jevbench | bb05a335bc809e61b20c0f745d25499a82b326fc | datasets/public/hard.jsonl | MIT |
| fancyzhx/ag_news | eb185aade064a813bc0b7f42de02595523103ca4 | data/test-00000-of-00001.parquet | ['unknown'] |
| google/boolq | 35b264d03638db9f4ce671b711558bf7ff0f80d5 | data/validation-00000-of-00001.parquet | ['cc-by-sa-3.0'] |
| facebook/anli | 8e4813d81f46d313dac7892e1c28076917cfcdf9 | plain_text/test_r1-00000-of-00001.parquet | ['cc-by-nc-4.0'] |
| facebook/anli | 8e4813d81f46d313dac7892e1c28076917cfcdf9 | plain_text/test_r2-00000-of-00001.parquet | ['cc-by-nc-4.0'] |
| facebook/anli | 8e4813d81f46d313dac7892e1c28076917cfcdf9 | plain_text/test_r3-00000-of-00001.parquet | ['cc-by-nc-4.0'] |
| SetFit/sst5 | e51bdcd8cd3a30da231967c1a249ba59361279a3 | test.jsonl | unspecified; local evaluation only, do not redistribute source text |
| sentence-transformers/stsb | ab7a5ac0e35aa22088bdcf23e7fd99b220e53308 | data/test-00000-of-00001.parquet | unspecified; local evaluation only, do not redistribute source text |
| facebook/belebele | 7899cdfa4e1e0d733fd77c848e2c273cb1d32be2 | data/zho_Hans.jsonl | cc-by-sa-4.0 |

Raw source text and responses remain local and gitignored; upstream licenses still apply.
Unspecified source licenses are not treated as permission to redistribute.
