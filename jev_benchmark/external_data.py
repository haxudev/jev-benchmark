"""Prepare pinned public datasets without calling a decision model."""

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import httpx
from huggingface_hub import HfApi, hf_hub_download

from .external import digest

SEED = 20261002
JEVBENCH_REVISION = "bb05a335bc809e61b20c0f745d25499a82b326fc"
SOURCES = {
    "ag_news": ("fancyzhx/ag_news", "eb185aade064a813bc0b7f42de02595523103ca4",
                ["data/test-00000-of-00001.parquet"]),
    "boolq": ("google/boolq", "35b264d03638db9f4ce671b711558bf7ff0f80d5",
              ["data/validation-00000-of-00001.parquet"]),
    "anli": ("facebook/anli", "8e4813d81f46d313dac7892e1c28076917cfcdf9",
             [f"plain_text/test_r{index}-00000-of-00001.parquet" for index in (1, 2, 3)]),
    "sst5": ("SetFit/sst5", "e51bdcd8cd3a30da231967c1a249ba59361279a3", ["test.jsonl"]),
    "stsb": ("sentence-transformers/stsb", "ab7a5ac0e35aa22088bdcf23e7fd99b220e53308",
             ["data/test-00000-of-00001.parquet"]),
    "belebele-zho_Hans": ("facebook/belebele", "7899cdfa4e1e0d733fd77c848e2c273cb1d32be2",
                          ["data/zho_Hans.jsonl"]),
}


def sample_rows(rows: list[dict], count: int, namespace: str) -> list[tuple[int, dict]]:
    if count <= 0 or count > len(rows):
        raise ValueError("Sample size must be positive and not exceed source rows.")
    ordered = sorted(enumerate(rows), key=lambda pair: digest([SEED, namespace, pair[0]]))
    return ordered[:count]


def labeled_item(identifier: str, suite: str, state: object, question: dict,
                 labels: list[str], target: int | None, target_score: float | None = None) -> dict:
    if len(set(labels)) != len(labels) or (target is not None and not 0 <= target < len(labels)):
        raise ValueError("Invalid labels or target.")
    return {"id": identifier, "suite": suite, "group": identifier, "state": state,
            "question": question, "labels": labels, "gold_index": target,
            "gold": [float(index == target) for index in range(len(labels))] if target is not None else None,
            "target_score": target_score}


def convert_row(suite: str, row: dict, identifier: str) -> dict:
    if suite == "ag_news":
        labels = ["world", "sports", "business", "science_technology"]
        criteria = dict(zip(labels, ["World and international affairs.", "Sports news.",
                                     "Business and financial news.", "Science and technology news."]))
        return labeled_item(identifier, suite, {"article": row["text"]}, {
            "type": "choice", "instructions": "Which news category best fits the article?", "criteria": criteria,
        }, labels, int(row["label"]))
    if suite == "boolq":
        return labeled_item(identifier, suite, {"passage": row["passage"], "question": row["question"]}, {
            "type": "noul", "instructions": "According to the passage, is the answer to the question yes?",
        }, ["no", "yes"], int(row["answer"]))
    if suite == "anli":
        labels = ["entailment", "neutral", "contradiction"]
        criteria = dict(zip(labels, ["The premise establishes that the hypothesis is true.",
                                     "The premise does not establish whether the hypothesis is true or false.",
                                     "The premise establishes that the hypothesis is false."]))
        return labeled_item(identifier, suite, {"premise": row["premise"], "hypothesis": row["hypothesis"]}, {
            "type": "choice", "instructions": "What is the relationship between the premise and hypothesis?",
            "criteria": criteria,
        }, labels, int(row["label"]))
    if suite == "sst5":
        return labeled_item(identifier, suite, {"sentence": row["text"]}, {
            "type": "score", "instructions": "Rate the sentiment of the sentence.",
            "criteria": ["Very negative", "Negative", "Neutral", "Positive", "Very positive"],
        }, [str(index) for index in range(5)], int(row["label"]), float(row["label"]))
    if suite == "stsb":
        target = float(row["score"]) * 5
        if not 0 <= target <= 5:
            raise ValueError("Expected STS-B source scores normalized to [0, 1].")
        return labeled_item(identifier, suite, {"sentence_1": row["sentence1"], "sentence_2": row["sentence2"]}, {
            "type": "score", "instructions": "How similar in meaning are the two sentences?",
            "criteria": ["Different topics and meanings", "Same topic but not equivalent",
                         "Some shared details but not equivalent", "Roughly equivalent with important differences",
                         "Mostly equivalent with minor differences", "Completely equivalent meaning"],
        }, [str(index) for index in range(6)], None, target)
    if suite == "belebele-zho_Hans":
        labels = list("ABCD")
        return labeled_item(identifier, suite, {"passage": row["flores_passage"], "question": row["question"]}, {
            "type": "choice", "instructions": "Which option answers the question according to the passage?",
            "criteria": {label: row[f"mc_answer{index}"].strip() for index, label in enumerate(labels, 1)},
        }, labels, int(row["correct_answer_num"]) - 1)
    raise ValueError(f"Unknown dataset: {suite}")


def reverse_options(item: dict) -> dict:
    if item["question"]["type"] != "choice":
        raise ValueError("Only Choice candidates may be reordered.")
    reversed_item = deepcopy(item)
    reversed_item["id"] += "-reversed"
    reversed_item["permutation_of"] = item["id"]
    reversed_item["labels"] = list(reversed(item["labels"]))
    reversed_item["question"]["criteria"] = {
        label: item["question"]["criteria"][label] for label in reversed_item["labels"]
    }
    reversed_item["gold"] = list(reversed(item["gold"]))
    reversed_item["gold_index"] = len(item["labels"]) - 1 - item["gold_index"]
    return reversed_item


def validate_reference(manifest: dict, reference: dict) -> None:
    primary = [item for item in manifest["items"] if not item.get("permutation_of")]
    if (
        digest(manifest) != reference["manifest_sha256"]
        or len(primary) != reference["primary_decisions"]
        or len(manifest["items"]) != reference["total_requests"]
        or {suite: sum(item["suite"] == suite for item in primary)
            for suite in {item["suite"] for item in primary}}
        != {suite: values["n"] for suite, values in reference["suites"].items()}
    ):
        raise ValueError("Manifest differs from the historical reference; do not run a purported same-data comparison.")


def prepare(
    output: Path, count: int = 200, *, jevbench_source_dir: Path | None = None,
    reference_summary: Path | None = None,
) -> dict:
    if output.exists():
        raise FileExistsError(output)
    items = []
    sources = []
    for cohort in ("easy", "original", "hard"):
        url = f"https://raw.githubusercontent.com/fstandhartinger/jevbench/{JEVBENCH_REVISION}/datasets/public/{cohort}.jsonl"
        if jevbench_source_dir is None:
            response = httpx.get(url, timeout=120, follow_redirects=True)
            response.raise_for_status()
            raw = response.content
        else:
            raw = (jevbench_source_dir / f"{cohort}.jsonl").read_bytes()
        rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        source = {"repo": "fstandhartinger/jevbench", "revision": JEVBENCH_REVISION,
                  "file": f"datasets/public/{cohort}.jsonl", "sha256": sha256(raw).hexdigest(),
                  "source_rows": len(rows), "license": "MIT"}
        sources.append(source)
        for row in rows:
            labels = [str(label) for label in row["labels"]]
            question = {key: row["question"][key] for key in ("type", "instructions", "criteria") if key in row["question"]}
            target = labels.index(str(row["expected"]))
            item = labeled_item(row["id"], f"jevbench-{cohort}", row["state"], question, labels, target,
                                float(row["expected"]) if question["type"] == "score" else None)
            item.update(group=row["group"], family=row["family"], source=source,
                        label_basis=row["provenance"].get("label_basis", "source reference"))
            items.append(item)
        print(f"Prepared JevBench {cohort}: {len(rows)}", flush=True)
    api = HfApi(token=False)
    for suite, (repo, revision, files) in SOURCES.items():
        info = api.dataset_info(repo, revision=revision)
        license_name = info.card_data.get("license") if info.card_data else None
        if not license_name:
            license_name = "unspecified; local evaluation only, do not redistribute source text"
            print(f"License unspecified: {repo}; artifacts remain local.", flush=True)
        for file_index, filename in enumerate(files):
            path = Path(hf_hub_download(repo, filename, repo_type="dataset", revision=revision, token=False))
            if filename.endswith(".parquet"):
                import pyarrow.parquet as parquet
                rows = parquet.read_table(path).to_pylist()
            else:
                rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            source = {"repo": repo, "revision": revision, "file": filename,
                      "sha256": sha256(path.read_bytes()).hexdigest(), "license": license_name,
                      "source_rows": len(rows)}
            sources.append(source)
            per_file = count // len(files) + int(file_index < count % len(files))
            for index, row in sample_rows(rows, per_file, suite + "/" + filename):
                identifier = f"{suite}-{file_index}-{index}"
                item = convert_row(suite, row, identifier)
                item.update(source=source, source_row=index, subset=filename,
                            label_basis="published dataset annotation")
                items.append(item)
        print(f"Prepared {suite}: {count}", flush=True)
    original_items = list(items)
    for suite in sorted({item["suite"] for item in original_items}):
        choices = [item for item in original_items if item["suite"] == suite and item["question"]["type"] == "choice"]
        limit = 10 if suite.startswith("jevbench-") else 20
        items.extend(reverse_options(item) for item in choices[:limit])
    manifest = {"name": "qwen35-4b-external-v1", "seed": SEED, "per_dataset": count,
                "sources": sources, "protocol": {
                    "sampling": "hash-ordered without label balancing; ANLI equally allocated across rounds",
                    "scope": "231 JevBench published items plus six public dataset slices; not the complete JevBench leaderboard",
                    "templates": "fixed native templates, not an exact replication of the 37-task paper",
                    "selection": "no model or temperature changes after observing these cases",
                    "probabilities": "native scalar-head probabilities; no response-token scoring or normalization",
                    "latency": "serial warm HTTP client; protocol probe excluded",
                }, "items": items}
    if reference_summary is not None:
        validate_reference(manifest, json.loads(reference_summary.read_text(encoding="utf-8")))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    print(f"Manifest: {len(original_items)} primary + {len(items) - len(original_items)} reversal = {len(items)} requests", flush=True)
    print(f"SHA-256: {digest(manifest)}", flush=True)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-dataset", type=int, default=200)
    parser.add_argument("--jevbench-source-dir", type=Path, help="Local pinned JevBench JSONL sources; verify the resulting manifest hash.")
    parser.add_argument("--reference-summary", type=Path, help="Require exact historical manifest hash and task counts.")
    arguments = parser.parse_args()
    prepare(
        arguments.output, arguments.per_dataset, jevbench_source_dir=arguments.jevbench_source_dir,
        reference_summary=arguments.reference_summary,
    )