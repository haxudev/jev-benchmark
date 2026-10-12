# microsoft-decision-1 External Evaluation

Model: `microsoft-decision-1`. Manifest SHA-256: `fbb21679cd930b0397a3adcc20d408e422cb816596f0921673ef5602621d4d02`.

Requested model: `Decision-1`. Run ended UTC: 2026-10-12T09:59:59.038550+00:00.

Requests recorded: 524/1521.

**Run status: failed**. Valid responses: 521/1521.

All configured items attempted: False. Minimum request-start interval: 1.25 seconds (excluded from measured request latency).

Incomplete or unattempted tasks are not assigned benchmark scores in this report. Fully attempted tasks count API failures as incorrect; probability metrics use valid responses only. The JSON retains strict planned-denominator accuracy for auditing failures.

| Suite | N | Attempted | Valid | Status | Accuracy | Brier (sum) | NLL | ECE | MAE | Spearman | p50 / p95 (s) |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ag_news | 200 | 200 | 199 | failed | 0.8900 | 0.1834 | 0.3669 | 0.0584 | N/A | N/A | 1.0059 / 1.6093 |
| anli | 200 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |
| belebele-zho_Hans | 200 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |
| boolq | 200 | 93 | 92 | incomplete | N/A | N/A | N/A | N/A | N/A | N/A | 0.9993 / 1.5508 |
| jevbench-easy | 48 | 48 | 48 | complete | 1.0000 | 0.0000 | 0.0025 | 0.0025 | N/A | N/A | 0.5105 / 1.0765 |
| jevbench-hard | 111 | 111 | 111 | complete | 0.8198 | 0.2609 | 0.4769 | 0.0408 | 0.4366 | 0.6172 | 0.5486 / 1.0813 |
| jevbench-original | 72 | 72 | 71 | failed | 0.9861 | 0.0015 | 0.0120 | 0.0116 | 0.0014 | 0.9608 | 0.5177 / 1.0922 |
| sst5 | 200 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |
| stsb | 200 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |

## Explicit continuation

Retained 277 original attempts, including 2 errors, from `external-microsoft-20261012-continued`. Sent 247 previously unattempted items; no saved attempt was resent.
Continuation started UTC: 2026-10-12T09:54:28.787947+00:00.

## Interpretation

- JevBench results cover only the pinned, published public cohorts, not the full leaderboard.
- Accuracy counts failures and unattempted items as incorrect; probability metrics use valid vectors only.
- Brier uses the multiclass sum convention. NLL floors probabilities at 1e-15 and reports zero-mass rows.
- ECE uses top-label probability and reference agreement, not the model's entropy-based confidence.
- Score tasks retain expected-level MAE and Spearman; continuous STS-B targets have no fabricated gold distribution.
- Risk/coverage curves are descriptive; no threshold or temperature is fitted on these test cases.
- Accuracy intervals resample whole scenario groups (1,000 bootstrap draws).
- Latency is serial HTTP client wall time, not normalized GPU throughput.
- No model tuning, retry, hidden probability normalization, or response-token scoring.
- Hosted API calls may be billed; no price or cost is inferred from token counts.
- Zero-shot means no benchmark-directed tuning in this run; pretraining and historical training overlap are not ruled out.
- Actual model identity was checked on every response; deployed weight hashes were not independently inspected.

## Failures

- ag_news: `{"connection_error_no_retry": 1}`
- anli: `{"unattempted": 200}`
- belebele-zho_Hans: `{"unattempted": 200}`
- boolq: `{"connection_error_no_retry": 1, "unattempted": 107}`
- jevbench-original: `{"http_429": 1}`
- sst5: `{"unattempted": 200}`
- stsb: `{"unattempted": 200}`

## Option Reversal

| Suite | Valid pairs | Same choice | Both correct |
| --- | ---: | ---: | ---: |
| ag_news | 0/20 | N/A | N/A |
| anli | 0/20 | N/A | N/A |
| belebele-zho_Hans | 0/20 | N/A | N/A |
| jevbench-easy | 0/10 | N/A | N/A |
| jevbench-hard | 0/10 | N/A | N/A |
| jevbench-original | 0/10 | N/A | N/A |

## High-Probability Decisions

Descriptive p_max >= 0.9 slice; these are not fitted deployment thresholds. Incomplete-task slices are diagnostics only, not completed benchmark results.

| Suite | Valid / N | Status | Accepted | Coverage | Error rate |
| --- | ---: | --- | ---: | ---: | ---: |
| ag_news | 199/200 | failed | 153 | 0.7650 | 0.0654 |
| boolq | 92/200 | incomplete | 75 | 0.3750 | 0.0533 |
| jevbench-easy | 48/48 | complete | 48 | 1.0000 | 0.0000 |
| jevbench-hard | 111/111 | complete | 58 | 0.5225 | 0.0345 |
| jevbench-original | 71/72 | failed | 69 | 0.9583 | 0.0000 |

## Systems

```json
{
  "actual_models": [
    "microsoft-decision-1"
  ],
  "valid_responses": 521,
  "mean_seconds": 0.8952946952290716,
  "p50_seconds": 0.9353119999977935,
  "p95_seconds": 1.5541845799976721,
  "sum_request_seconds": 469.1344203000335,
  "reported_input_tokens": null,
  "reported_output_tokens": null,
  "cost_usd": null,
  "cost_basis": "hosted API; billed cost was not measured"
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
