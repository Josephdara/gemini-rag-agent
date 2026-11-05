import asyncio
import json
from datetime import datetime, timezone

import pytest

from fakes import FakeResponse, FakeSession
from rag_eval import EVAL_ROOT, __main__ as run
from rag_eval.record import build_record

CONFIG = run.load_config()
PASSING = {"name": "m", "definition": "d", "value": 1.0, "threshold": 1.0, "comparison": "min", "passed": True}
ITEM = {"id": "q1", "question": "How long?", "expected_sources": ["returns.md"], "reference": "30 days."}


def schema_fields(schema):
    return {field["name"]: field for field in schema}


def sample_record(settings, item_limit=None):
    return build_record(
        run_id="r1",
        run_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        config=CONFIG,
        settings=settings,
        dataset_sha256="abc",
        dataset_item_count=10,
        item_count=10 if item_limit is None else item_limit,
        item_limit=item_limit,
        item_errors=0,
        instruction_sha256="def",
        rubric_sha256="ghi",
        metrics=[PASSING],
        harness_version="0.1.0",
        report_path="eval/reports/r1.json",
    )


def test_record_matches_the_eval_runs_table_schema(test_settings):
    fields = schema_fields(json.loads((EVAL_ROOT / "schema" / "eval_runs.json").read_text()))
    record = sample_record(test_settings)
    assert set(record) == set(fields)
    for name, field in fields.items():
        if field["mode"] == "REQUIRED":
            assert record[name] is not None, name
    assert set(record["metrics"][0]) == set(schema_fields(fields["metrics"]["fields"]))


def test_a_limited_run_never_passes(test_settings):
    assert sample_record(test_settings)["passed"]
    assert not sample_record(test_settings, item_limit=5)["passed"]


def test_dataset_items_are_complete():
    items = run.parse_dataset((EVAL_ROOT / "datasets" / "v1.jsonl").read_bytes())
    assert len({item["id"] for item in items}) == len(items)
    assert all(set(item) == set(ITEM) for item in items)


def test_an_item_is_scored_from_the_agent_turn():
    async def fake_ask(question):
        retrieved = [{"citation": "returns.md#0", "text": "30 days"}]
        return {"answer": "30 days [returns.md#0].", "retrieved": retrieved, "seconds": 1.5}

    sess = FakeSession(FakeResponse(200, {"pointwiseMetricResult": {"score": 5, "explanation": "good"}}))
    result = asyncio.run(run.score_item(sess, "p", CONFIG, "{response}", ITEM, ask_fn=fake_ask))
    assert (result["hit"], result["reciprocal_rank"], result["citation_valid"]) == (1.0, 1.0, True)
    assert result["judge_score"] == 5.0
    judged = json.loads(sess.calls[0][1]["pointwiseMetricInput"]["instance"]["jsonInstance"])
    assert judged["context"] == "[returns.md#0] 30 days"


def test_an_agent_failure_is_recorded_on_the_item():
    async def failing_ask(question):
        raise RuntimeError("quota")

    result = asyncio.run(run.score_item(FakeSession(), "p", CONFIG, "", ITEM, ask_fn=failing_ask))
    assert result["error"] == "RuntimeError: quota"


def test_runs_cannot_overlap(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "REPORTS", tmp_path)
    with run.single_run_lock():
        with pytest.raises(SystemExit):
            with run.single_run_lock():
                pass
    assert not (tmp_path / ".lock").exists()
