import json
from pathlib import Path

import pytest


def _make_risk(i, *, with_mitigations=False, with_causal=False):
    risk = {
        "risk_id": f"atlas-risk-{i}",
        "risk_name": f"Risk {i}",
        "risk_description": f"Description for risk {i}",
        "taxonomy": "ibm-risk-atlas",
        "confidence": round(0.9 - i * 0.1, 2),
        "grounding_confidence": "high" if i % 2 == 0 else "medium",
        "accepted_by": "rrf",
        "evidence": [
            {
                "text": f"Evidence text for risk {i}",
                "document": "policy.pdf",
                "page": 1,
                "section": "Section 1",
                "chunk_index": 0,
                "sentence_index": 0,
                "cross_encoder_score": 0.85,
            }
        ],
        "scores": {
            "bm25_rank": i,
            "embedding_distance": 0.3,
            "cross_encoder_score": 0.8,
            "rrf_score": 0.5,
        },
    }
    if with_mitigations:
        risk["mitigations"] = [
            {
                "action_id": f"owasp-act-{i}-01",
                "action_name": f"Mitigation {i}-1",
                "description": "Apply controls",
                "source": "owasp-llm-2.0",
                "category": "technical",
                "risk_control": "MitigationControl",
            },
            {
                "action_id": f"nist-act-{i}-01",
                "action_name": f"Mitigation {i}-2",
                "description": "Monitor system",
                "source": "nist-ai-rmf",
                "category": "operational",
                "risk_control": "MonitorControl",
            },
        ]
    if with_causal:
        risk["threat"] = f"Threat for risk {i}"
        risk["threat_source"] = f"Threat source for risk {i}"
        risk["vulnerability"] = f"Vulnerability for risk {i}"
        risk["consequence"] = f"Consequence for risk {i}"
        risk["impact"] = f"Impact for risk {i}"
    return risk


def _make_extraction(num_risks=3, *, with_mitigations=False, with_causal=False):
    return {
        "version": "0.3",
        "risks": [
            _make_risk(i, with_mitigations=with_mitigations, with_causal=with_causal)
            for i in range(num_risks)
        ],
        "source_documents": ["policy.pdf"],
        "token_usage": {"prompt": 1000, "completion": 500, "total": 1500},
        "retrieval_stats": {
            "total_chunks": 10,
            "total_candidates_retrieved": 20,
            "auto_accepted": 3,
            "llm_judged": 2,
            "grounding_filtered": 1,
            "timing_ms": {},
        },
        "metadata": {
            "model": "test-model",
            "timestamp": "2026-06-01T12:00:00Z",
        },
        "chunks": [],
        "llm_calls": [],
        "grounding_filtered_candidates": [],
        "eval": None,
    }


@pytest.fixture
def tmp_runs(tmp_path):
    for name, num_risks in [("run-alpha", 3), ("run-beta", 5)]:
        d = tmp_path / name
        d.mkdir()
        data = _make_extraction(num_risks, with_mitigations=True, with_causal=True)
        (d / "risk-extraction.json").write_text(json.dumps(data))
    return tmp_path


@pytest.fixture
def tmp_policies(tmp_path):
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "banking-policy.md").write_text("# Banking Policy")
    (examples / "healthcare.json").write_text('{"policies": []}')
    (examples / "report.pdf").write_bytes(b"%PDF-1.4 fake")
    (examples / ".hidden").write_text("should be ignored")
    sub = examples / "multi-doc-group"
    sub.mkdir()
    (sub / "part1.md").write_text("# Part 1")
    return examples


@pytest.fixture
def tmp_sssom(tmp_path):
    tsv = tmp_path / "risk_to_category.sssom.tsv"
    lines = [
        "# comment line",
        "subject_id\tsubject_source\tpredicate_id\tobject_id\tobject_source\tmapping_justification",
        "atlas-risk-0\tibm-risk-atlas\tskos:exactMatch\tnist-data-privacy\tnist-ai-rmf\ttest",
        "atlas-risk-0\tibm-risk-atlas\tskos:broadMatch\tail-privacy\tailuminate-v1.0\ttest",
        "atlas-risk-1\tibm-risk-atlas\tskos:closeMatch\tnist-confabulation\tnist-ai-rmf\ttest",
        "atlas-risk-1\tibm-risk-atlas\tskos:relatedMatch\tail-hate\tailuminate-v1.0\ttest",
        "atlas-risk-2\tibm-risk-atlas\tskos:exactMatch\tllm022025-sensitive-information-disclosure\towasp-llm-2.0\ttest",
    ]
    tsv.write_text("\n".join(lines) + "\n")
    return tsv
