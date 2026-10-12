# jev-1.13.0 External Evaluation

Model: `jev-1.13.0`. Manifest SHA-256: `fbb21679cd930b0397a3adcc20d408e422cb816596f0921673ef5602621d4d02`.

Requested model: `jev-1.13.0`. Run ended UTC: 2026-10-12T11:44:14.470632+00:00.

Requests recorded: 1521/1521.

**Run status: complete**. Valid responses: 1521/1521.

All configured items attempted: True. Minimum request-start interval: 0.25 seconds (excluded from measured request latency).

Network error policy: `record_and_continue_next_item; stop_after_3_consecutive; never_retry`. Keepalive for this segment's new requests: True. Retained responses keep their original transport conditions.

Probability reporting: Jev 1.13 hundredths: feasible rounding bounds, native Score retained, no normalization. Jev hundredths are not renormalized; rounded zero probabilities can inflate floored NLL, and its native reported Score is retained for MAE and Spearman.

Incomplete or unattempted tasks are not assigned benchmark scores in this report. Fully attempted tasks count API failures as incorrect; probability metrics use valid responses only. The JSON retains strict planned-denominator accuracy for auditing failures.

| Suite | N | Attempted | Valid | Status | Accuracy | Brier (sum) | NLL | ECE | MAE | Spearman | p50 / p95 (s) |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ag_news | 200 | 200 | 200 | complete | 0.8700 | 0.2083 | 1.9139 | 0.0876 | N/A | N/A | 0.2506 / 0.2930 |
| anli | 200 | 200 | 200 | complete | 0.7150 | 0.4234 | 1.4919 | 0.1340 | N/A | N/A | 0.2589 / 0.3277 |
| belebele-zho_Hans | 200 | 200 | 200 | complete | 0.9400 | 0.0926 | 0.4903 | 0.0338 | N/A | N/A | 0.2517 / 0.3056 |
| boolq | 200 | 200 | 200 | complete | 0.9000 | 0.1572 | 0.2665 | 0.0250 | N/A | N/A | 0.2549 / 0.3041 |
| jevbench-easy | 48 | 48 | 48 | complete | 1.0000 | 0.0002 | 0.0044 | 0.0044 | N/A | N/A | 0.2529 / 0.5869 |
| jevbench-hard | 111 | 111 | 111 | complete | 0.7207 | 0.3517 | 0.5967 | 0.0847 | 0.3767 | 0.7715 | 0.2487 / 0.2962 |
| jevbench-original | 72 | 72 | 72 | complete | 0.9861 | 0.0269 | 0.0562 | 0.0453 | 0.0033 | 0.9852 | 0.2514 / 0.3688 |
| sst5 | 200 | 200 | 200 | complete | 0.5200 | 0.7219 | 3.0408 | 0.2502 | 0.5978 | 0.7996 | 0.2569 / 0.3022 |
| stsb | 200 | 200 | 200 | complete | N/A | N/A | N/A | N/A | 0.5055 | 0.9015 | 0.2533 / 0.3226 |

## Explicit continuation

Retained 81 original attempts, including 0 errors, from `external-jev-20261012`. Sent 1440 previously unattempted items; no saved attempt was resent.
Continuation started UTC: 2026-10-12T11:37:44.214694+00:00.

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
| ag_news | 20/20 | 1.0000 | 0.8500 |
| anli | 20/20 | 0.9500 | 0.7500 |
| belebele-zho_Hans | 20/20 | 1.0000 | 0.9000 |
| jevbench-easy | 10/10 | 1.0000 | 1.0000 |
| jevbench-hard | 10/10 | 1.0000 | 0.5000 |
| jevbench-original | 10/10 | 1.0000 | 1.0000 |

## High-Probability Decisions

Descriptive p_max >= 0.9 slice; these are not fitted deployment thresholds. Incomplete-task slices are diagnostics only, not completed benchmark results.

| Suite | Valid / N | Status | Accepted | Coverage | Error rate |
| --- | ---: | --- | ---: | ---: | ---: |
| ag_news | 200/200 | complete | 176 | 0.8800 | 0.0852 |
| anli | 200/200 | complete | 103 | 0.5150 | 0.1553 |
| belebele-zho_Hans | 200/200 | complete | 178 | 0.8900 | 0.0169 |
| boolq | 200/200 | complete | 153 | 0.7650 | 0.0523 |
| jevbench-easy | 48/48 | complete | 48 | 1.0000 | 0.0000 |
| jevbench-hard | 111/111 | complete | 44 | 0.3964 | 0.0227 |
| jevbench-original | 72/72 | complete | 65 | 0.9028 | 0.0000 |
| sst5 | 200/200 | complete | 54 | 0.2700 | 0.3704 |

## Systems

```json
{
  "actual_models": [
    "jev-1.13.0"
  ],
  "valid_responses": 1521,
  "mean_seconds": 0.2673516890203393,
  "p50_seconds": 0.25353309999627527,
  "p95_seconds": 0.30775350000476465,
  "sum_request_seconds": 406.641918999936,
  "reported_input_tokens": 787303,
  "reported_output_tokens": 52530,
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
