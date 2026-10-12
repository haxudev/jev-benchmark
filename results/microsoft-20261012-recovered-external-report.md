# microsoft-decision-1 External Evaluation

Model: `microsoft-decision-1`. Manifest SHA-256: `fbb21679cd930b0397a3adcc20d408e422cb816596f0921673ef5602621d4d02`.

Requested model: `Decision-1`. Run ended UTC: 2026-10-12T12:35:31.522996+00:00.

Logical items recorded: 1521/1521. Physical HTTP attempts: 1537.

**Run status: complete**. Valid responses: 1521/1521.

All configured items attempted: True. Minimum request-start interval: 1.25 seconds (excluded from measured request latency).

Network error policy: `explicit_recovery_only; no_automatic_retry`. Keepalive for this segment's new requests: True. Retained responses keep their original transport conditions.

Probability reporting: native reported values; no normalization. Jev hundredths are not renormalized; rounded zero probabilities can inflate floored NLL, and its native reported Score is retained for MAE and Spearman.

Incomplete or unattempted tasks are not assigned benchmark scores in this report. Fully attempted tasks count API failures as incorrect; probability metrics use valid responses only. The JSON retains strict planned-denominator accuracy for auditing failures.

| Suite | N | Attempted | Valid | Status | Accuracy | Brier (sum) | NLL | ECE | MAE | Spearman | p50 / p95 (s) |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ag_news | 200 | 200 | 200 | complete | 0.8950 | 0.1825 | 0.3653 | 0.0579 | N/A | N/A | 1.0039 / 1.6088 |
| anli | 200 | 200 | 200 | complete | 0.6350 | 0.5021 | 0.8749 | 0.1604 | N/A | N/A | 1.3907 / 1.9369 |
| belebele-zho_Hans | 200 | 200 | 200 | complete | 0.9700 | 0.0364 | 0.0933 | 0.0454 | N/A | N/A | 1.3807 / 1.9352 |
| boolq | 200 | 200 | 200 | complete | 0.8650 | 0.1906 | 0.3145 | 0.0727 | N/A | N/A | 1.3246 / 1.9285 |
| jevbench-easy | 48 | 48 | 48 | complete | 1.0000 | 0.0000 | 0.0025 | 0.0025 | N/A | N/A | 0.5105 / 1.0765 |
| jevbench-hard | 111 | 111 | 111 | complete | 0.8198 | 0.2609 | 0.4769 | 0.0408 | 0.4366 | 0.6172 | 0.5486 / 1.0813 |
| jevbench-original | 72 | 72 | 72 | complete | 1.0000 | 0.0014 | 0.0118 | 0.0114 | 0.0014 | 0.9608 | 0.5187 / 1.0992 |
| sst5 | 200 | 200 | 200 | complete | 0.5300 | 0.5946 | 1.0570 | 0.1057 | 0.5520 | 0.8383 | 1.3883 / 1.8997 |
| stsb | 200 | 200 | 200 | complete | N/A | N/A | N/A | N/A | 0.4472 | 0.9296 | 1.3801 / 1.8915 |

## User-directed missing-answer recovery

Original valid answers: 1505. Explicit additional attempts: 16. Only items lacking valid responses were sent again; valid wrong predictions were not repeated.
Source snapshot: `external-microsoft-20261012-continued3`. Original responses and the complete physical attempt history remain local and unchanged.
First-pass failed attempts retained: 16.

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

No failed or invalid primary responses.

## Option Reversal

| Suite | Valid pairs | Same choice | Both correct |
| --- | ---: | ---: | ---: |
| ag_news | 20/20 | 1.0000 | 0.9000 |
| anli | 20/20 | 1.0000 | 0.7500 |
| belebele-zho_Hans | 20/20 | 1.0000 | 1.0000 |
| jevbench-easy | 10/10 | 1.0000 | 1.0000 |
| jevbench-hard | 10/10 | 1.0000 | 0.8000 |
| jevbench-original | 10/10 | 1.0000 | 1.0000 |

## High-Probability Decisions

Descriptive p_max >= 0.9 slice; these are not fitted deployment thresholds. Incomplete-task slices are diagnostics only, not completed benchmark results.

| Suite | Valid / N | Status | Accepted | Coverage | Error rate |
| --- | ---: | --- | ---: | ---: | ---: |
| ag_news | 200/200 | complete | 154 | 0.7700 | 0.0649 |
| anli | 200/200 | complete | 63 | 0.3150 | 0.2222 |
| belebele-zho_Hans | 200/200 | complete | 171 | 0.8550 | 0.0000 |
| boolq | 200/200 | complete | 161 | 0.8050 | 0.0497 |
| jevbench-easy | 48/48 | complete | 48 | 1.0000 | 0.0000 |
| jevbench-hard | 111/111 | complete | 58 | 0.5225 | 0.0345 |
| jevbench-original | 72/72 | complete | 70 | 0.9722 | 0.0000 |
| sst5 | 200/200 | complete | 1 | 0.0050 | 1.0000 |

## Systems

```json
{
  "actual_models": [
    "microsoft-decision-1"
  ],
  "valid_responses": 1521,
  "mean_seconds": 1.2740675506246086,
  "p50_seconds": 1.308482799999183,
  "p95_seconds": 1.8999522999947658,
  "sum_request_seconds": 1937.85674450003,
  "reported_input_tokens": 327004,
  "reported_output_tokens": 1521,
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
