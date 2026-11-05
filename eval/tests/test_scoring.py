import json

import pytest

from fakes import FakeResponse, FakeSession
from rag_eval import EVAL_ROOT
from rag_eval.scoring import aggregate, apply_thresholds, citation_valid, citations, judge_score, p95, retrieval_scores

RETRIEVED = [{"citation": "shipping.md#1", "text": "..."}, {"citation": "returns.md#0", "text": "..."}]
THRESHOLDS = json.loads((EVAL_ROOT / "config.json").read_text())["thresholds"]


def test_p95_uses_nearest_rank():
    assert p95(list(range(1, 21))) == 19
    assert p95([3.0]) == 3.0


def test_citations_are_found_in_brackets():
    assert citations("Yes [returns.md#0]. Also [a/b.md#12], not [note] or [x #1].") == {"returns.md#0", "a/b.md#12"}
    assert citations("Grouped [a.md#0, b.md#1][c.md#2].") == {"a.md#0", "b.md#1", "c.md#2"}


def test_retrieval_scores_use_the_first_expected_source():
    assert retrieval_scores(RETRIEVED, ["returns.md"]) == (1.0, 0.5)
    assert retrieval_scores(RETRIEVED, ["warranty.md"]) == (0.0, 0.0)
    assert retrieval_scores(RETRIEVED, []) == (None, None)


def test_citations_must_name_retrieved_chunks():
    assert citation_valid("30 days [returns.md#0].", RETRIEVED, ["returns.md"])
    assert not citation_valid("30 days.", RETRIEVED, ["returns.md"])
    assert not citation_valid("30 days [returns.md#9].", RETRIEVED, ["returns.md"])
    assert citation_valid("I could not find that in the documents.", RETRIEVED, [])


def test_failed_items_count_against_the_run():
    results = [
        {"expected_sources": ["a.md"], "hit": 1.0, "reciprocal_rank": 1.0, "citation_valid": True,
         "judge_score": 5.0, "latency_seconds": 2.0},
        {"expected_sources": ["a.md"], "error": "ApiError: 503"},
        {"expected_sources": [], "hit": None, "reciprocal_rank": None, "citation_valid": True,
         "judge_score": 5.0, "latency_seconds": 4.0},
    ]
    values = aggregate(results)
    assert values["hit_rate"] == 0.5
    assert values["mrr"] == 0.5
    assert values["citation_rate"] == pytest.approx(2 / 3)
    assert values["judge_mean"] == pytest.approx(11 / 3)
    assert values["latency_p95_seconds"] == 4.0
    metrics = {m["name"]: m for m in apply_thresholds(values, THRESHOLDS)}
    assert not metrics["hit_rate"]["passed"]
    assert metrics["latency_p95_seconds"]["passed"]


def test_judge_names_the_global_model_from_the_regional_service():
    sess = FakeSession(FakeResponse(200, {"pointwiseMetricResult": {"score": 4, "explanation": "ok"}}))
    judge = {"model": "gemini-test", "location": "global"}
    assert judge_score(sess, "p", "us-east4", judge, "{response}", {"response": "r"}) == (4.0, "ok")
    url, body = sess.calls[0]
    assert url == "https://us-east4-aiplatform.googleapis.com/v1beta1/projects/p/locations/us-east4:evaluateInstances"
    assert body["autoraterConfig"]["autoraterModel"] == "projects/p/locations/global/publishers/google/models/gemini-test"
    assert body["allowCrossRegionModel"] is True


def test_judge_rejects_scores_outside_the_rubric():
    sess = FakeSession(FakeResponse(200, {"pointwiseMetricResult": {"score": 7}}))
    with pytest.raises(ValueError):
        judge_score(sess, "p", "us-east4", {"model": "m", "location": "global"}, "", {})


def test_rubric_placeholders_match_the_judge_instance():
    rubric = (EVAL_ROOT / "rubrics" / "groundedness-v1.txt").read_text()
    for name in ("question", "reference", "context", "response"):
        assert "{" + name + "}" in rubric
