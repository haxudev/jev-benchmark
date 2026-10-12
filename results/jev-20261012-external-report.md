# jev-1.13.0 External Evaluation

Model: `jev-1.13.0`. Manifest SHA-256: `fbb21679cd930b0397a3adcc20d408e422cb816596f0921673ef5602621d4d02`.

Requested model: `jev-1.13.0`. Run ended UTC: 2026-10-12T11:29:52.125245+00:00.

Requests recorded: 81/1521.

**Run status: failed**. Valid responses: 81/1521.

All configured items attempted: False. Minimum request-start interval: 0.25 seconds (excluded from measured request latency).

Network error policy: `record_and_continue_next_item; stop_after_3_consecutive; never_retry`. Keepalive for this segment's new requests: True. Retained responses keep their original transport conditions.

Incomplete or unattempted tasks are not assigned benchmark scores in this report. Fully attempted tasks count API failures as incorrect; probability metrics use valid responses only. The JSON retains strict planned-denominator accuracy for auditing failures.

| Suite | N | Attempted | Valid | Status | Accuracy | Brier (sum) | NLL | ECE | MAE | Spearman | p50 / p95 (s) |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ag_news | 200 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |
| anli | 200 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |
| belebele-zho_Hans | 200 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |
| boolq | 200 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |
| jevbench-easy | 48 | 48 | 48 | complete | 1.0000 | 0.0002 | 0.0044 | 0.0044 | N/A | N/A | 0.2529 / 0.5869 |
| jevbench-hard | 111 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |
| jevbench-original | 72 | 33 | 33 | incomplete | N/A | N/A | N/A | N/A | N/A | N/A | 0.2511 / 0.4578 |
| sst5 | 200 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |
| stsb | 200 | 0 | 0 | unattempted | N/A | N/A | N/A | N/A | N/A | N/A | N/A / N/A |

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

- ag_news: `{"unattempted": 200}`
- anli: `{"unattempted": 200}`
- belebele-zho_Hans: `{"unattempted": 200}`
- boolq: `{"unattempted": 200}`
- jevbench-hard: `{"unattempted": 111}`
- jevbench-original: `{"unattempted": 39}`
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
| jevbench-easy | 48/48 | complete | 48 | 1.0000 | 0.0000 |
| jevbench-original | 33/72 | incomplete | 29 | 0.4028 | 0.0000 |

## Systems

```json
{
  "actual_models": [
    "jev-1.13.0"
  ],
  "valid_responses": 81,
  "mean_seconds": 0.28943233703682414,
  "p50_seconds": 0.2516512999936822,
  "p95_seconds": 0.5852797999978065,
  "sum_request_seconds": 23.444019299982756,
  "reported_input_tokens": 29709,
  "reported_output_tokens": 3320,
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
