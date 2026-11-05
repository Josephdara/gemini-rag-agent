import json
import math
import re

from .api import api_host, post_json

# One citation per bracket, or several separated by commas: [a.md#0] or [a.md#0, b.md#2].
CITATION = re.compile(r"\[([^\[\]\s,]+#\d+(?:\s*,\s*[^\[\]\s,]+#\d+)*)\]")


def p95(values):
    if not values:
        raise ValueError("no values")
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def citations(answer):
    return {cited.strip() for group in CITATION.findall(answer) for cited in group.split(",")}


def retrieval_scores(retrieved, expected_sources):
    """Hit and reciprocal rank of the first retrieved chunk from an expected source; None when no source is
    expected, as for a question the documents cannot answer."""
    if not expected_sources:
        return None, None
    for rank, chunk in enumerate(retrieved, start=1):
        if chunk["citation"].split("#")[0] in expected_sources:
            return 1.0, 1.0 / rank
    return 0.0, 0.0


def citation_valid(answer, retrieved, expected_sources):
    """An answerable question needs at least one citation; every citation must name a retrieved chunk."""
    cited = citations(answer)
    if expected_sources and not cited:
        return False
    return cited <= {chunk["citation"] for chunk in retrieved}


def judge_score(sess, project, location, judge, template, instance):
    # The judge model is not served in the evaluation service's region, so the request names it on the global
    # endpoint and allows a cross-region call; this v1beta1 field is not in the public API reference.
    url = f"{api_host(location)}/v1beta1/projects/{project}/locations/{location}:evaluateInstances"
    body = {
        "pointwiseMetricInput": {
            "metricSpec": {"metricPromptTemplate": template},
            "instance": {"jsonInstance": json.dumps(instance)},
        },
        "autoraterConfig": {
            "autoraterModel": f"projects/{project}/locations/{judge['location']}/publishers/google/models/{judge['model']}"
        },
        "allowCrossRegionModel": True,
    }
    result = post_json(sess, url, body)["pointwiseMetricResult"]
    score = float(result["score"])
    if not 1.0 <= score <= 5.0:
        raise ValueError(f"judge score {score} is outside the 1 to 5 rubric")
    return score, result.get("explanation", "")


def aggregate(results):
    """Failed items count against the run: no retrieval or citation credit and the lowest rubric score. Retrieval
    metrics cover answerable questions; latency covers items whose agent call succeeded."""
    answerable = [r for r in results if r["expected_sources"]]
    latencies = [r["latency_seconds"] for r in results if r.get("latency_seconds") is not None]
    return {
        "hit_rate": sum(r.get("hit") or 0.0 for r in answerable) / len(answerable) if answerable else 0.0,
        "mrr": sum(r.get("reciprocal_rank") or 0.0 for r in answerable) / len(answerable) if answerable else 0.0,
        "citation_rate": sum(bool(r.get("citation_valid")) for r in results) / len(results),
        "judge_mean": sum(r.get("judge_score", 1.0) for r in results) / len(results),
        "latency_p95_seconds": p95(latencies) if latencies else 0.0,
    }


def apply_thresholds(values, thresholds):
    metrics = []
    for name, threshold in thresholds.items():
        value = values[name]
        if threshold["comparison"] == "min":
            passed = value >= threshold["value"]
        elif threshold["comparison"] == "max":
            passed = value <= threshold["value"]
        else:
            raise ValueError(f"unknown comparison {threshold['comparison']}")
        metrics.append(
            {
                "name": name,
                "definition": threshold["definition"],
                "value": float(value),
                "threshold": float(threshold["value"]),
                "comparison": threshold["comparison"],
                "passed": passed,
            }
        )
    return metrics
