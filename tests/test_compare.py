from concorde_policy_mapper_web.compare import build_comparison


def _make_run(name, risk_ids):
    return {
        "name": name,
        "data": {
            "version": "0.3",
            "risks": [
                {
                    "risk_id": rid,
                    "risk_name": rid.replace("-", " ").title(),
                    "taxonomy": "ibm-risk-atlas",
                    "confidence": 0.8,
                    "grounding_confidence": "high",
                    "evidence": [{"text": "ev"}],
                    "mitigations": [],
                }
                for rid in risk_ids
            ],
            "source_documents": ["doc.pdf"],
            "metadata": {"model": "test", "timestamp": "2026-06-01T12:00:00Z"},
        },
    }


def test_build_comparison_shared_risks():
    runs = [
        _make_run("run-a", ["risk-1", "risk-2", "risk-3"]),
        _make_run("run-b", ["risk-2", "risk-3", "risk-4"]),
    ]
    result = build_comparison(runs)
    shared_ids = {r["risk_id"] for r in result["shared_risks"]}
    assert shared_ids == {"risk-2", "risk-3"}


def test_build_comparison_unique_risks():
    runs = [
        _make_run("run-a", ["risk-1", "risk-2"]),
        _make_run("run-b", ["risk-2", "risk-3"]),
    ]
    result = build_comparison(runs)
    assert "risk-1" in {r["risk_id"] for r in result["unique_risks"]["run-a"]}
    assert "risk-3" in {r["risk_id"] for r in result["unique_risks"]["run-b"]}


def test_build_comparison_confidence():
    runs = [
        _make_run("run-a", ["risk-1"]),
        _make_run("run-b", ["risk-1"]),
    ]
    runs[0]["data"]["risks"][0]["confidence"] = 0.9
    runs[1]["data"]["risks"][0]["confidence"] = 0.7
    result = build_comparison(runs)
    shared = result["shared_risks"][0]
    assert shared["per_run"]["run-a"]["confidence"] == 0.9
    assert shared["per_run"]["run-b"]["confidence"] == 0.7


def test_build_comparison_run_summaries():
    runs = [
        _make_run("run-a", ["risk-1"]),
        _make_run("run-b", ["risk-1", "risk-2"]),
    ]
    result = build_comparison(runs)
    summaries = {s["name"]: s for s in result["summaries"]}
    assert summaries["run-a"]["risk_count"] == 1
    assert summaries["run-b"]["risk_count"] == 2
