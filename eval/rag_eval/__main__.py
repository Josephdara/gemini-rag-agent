"""Scores retrieval and answers for the dataset, one question at a time: python -m rag_eval"""

import argparse
import asyncio
import hashlib
import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from . import EVAL_ROOT, __version__
from .agent_run import ask
from .api import session
from .record import build_record
from .scoring import aggregate, apply_thresholds, citation_valid, judge_score, retrieval_scores

REPORTS = EVAL_ROOT / "reports"


def sha256(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


def load_config():
    return json.loads((EVAL_ROOT / "config.json").read_text())


def parse_dataset(data):
    return [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]


@contextmanager
def single_run_lock():
    """Refuses to start while another run holds the lock, so runs never overlap."""
    REPORTS.mkdir(exist_ok=True)
    lock = REPORTS / ".lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit(f"another evaluation run holds {lock}; delete it if no run is active") from None
    try:
        os.write(fd, str(os.getpid()).encode())
        yield
    finally:
        os.close(fd)
        lock.unlink()


async def score_item(sess, project, config, rubric, item, ask_fn=ask):
    """Scores one item. A failure is recorded on the item instead of ending the run."""
    result = {"id": item["id"], "expected_sources": item["expected_sources"]}
    try:
        call = await ask_fn(item["question"])
        answer, retrieved = call["answer"], call["retrieved"]
        result.update(latency_seconds=call["seconds"], answer=answer, retrieved=[c["citation"] for c in retrieved])
        result["hit"], result["reciprocal_rank"] = retrieval_scores(retrieved, item["expected_sources"])
        result["citation_valid"] = citation_valid(answer, retrieved, item["expected_sources"])
        instance = {
            "question": item["question"],
            "reference": item["reference"],
            "context": "\n\n".join(f"[{c['citation']}] {c['text']}" for c in retrieved) or "(no passages retrieved)",
            "response": answer,
        }
        result["judge_score"], result["judge_explanation"] = judge_score(
            sess, project, config["evaluation_location"], config["judge"], rubric, instance
        )
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"[:1000]
    return result


async def score_items(sess, project, config, rubric, items, pause_seconds):
    """Scores items one at a time with a pause between them, in one event loop so the agent's clients stay valid."""
    results = []
    for index, item in enumerate(items):
        if index:
            await asyncio.sleep(pause_seconds)
        results.append(await score_item(sess, project, config, rubric, item))
        outcome = results[-1].get("error") or f"judge {results[-1]['judge_score']}"
        print(f"{index + 1}/{len(items)} {item['id']}: {outcome}", flush=True)
    return results


def insert_record(project, table, record):
    from google.cloud import bigquery

    errors = bigquery.Client(project=project).insert_rows_json(table, [record], row_ids=[record["run_id"]])
    if errors:
        raise RuntimeError(f"failed to insert the evaluation record: {errors}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="evaluate only the first N items; such a run never passes")
    parser.add_argument("--pause-seconds", type=float, default=5.0, help="wait between items")
    args = parser.parse_args(argv)

    from rag_agent.agent import INSTRUCTION
    from rag_agent.config import settings

    s = settings()
    config = load_config()
    data = (EVAL_ROOT / "datasets" / f"{config['dataset_version']}.jsonl").read_bytes()
    rubric = (EVAL_ROOT / config["rubric"]).read_text()
    items = parse_dataset(data)
    selected = items[: args.limit] if args.limit else items
    run_id, run_time = str(uuid.uuid4()), datetime.now(timezone.utc)
    sess = session()

    with single_run_lock():
        results = asyncio.run(score_items(sess, s.project, config, rubric, selected, args.pause_seconds))

    metrics = apply_thresholds(aggregate(results), config["thresholds"])
    report_path = REPORTS / f"{run_id}.json"
    record = build_record(
        run_id=run_id,
        run_time=run_time,
        config=config,
        settings=s,
        dataset_sha256=sha256(data),
        dataset_item_count=len(items),
        item_count=len(selected),
        item_limit=args.limit,
        item_errors=sum("error" in r for r in results),
        instruction_sha256=sha256(INSTRUCTION),
        rubric_sha256=sha256(rubric),
        metrics=metrics,
        harness_version=__version__,
        report_path=str(report_path.relative_to(EVAL_ROOT.parent)),
    )
    report_path.write_text(json.dumps({"record": record, "items": results}, indent=2))
    insert_record(s.project, f"{s.project}.{s.bq_dataset}.eval_runs", record)
    for metric in metrics:
        status = "pass" if metric["passed"] else "FAIL"
        print(f"{status} {metric['name']} = {metric['value']:.3f} ({metric['comparison']} {metric['threshold']})")
    print(f"run {run_id} {'passed' if record['passed'] else 'did not pass'}; report: {record['report_path']}")


if __name__ == "__main__":
    main()
