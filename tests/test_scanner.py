from pathlib import Path

from concorde_policy_mapper_web.scanner import (
    list_runs,
    load_run,
    load_category_map,
    list_policies,
)


def test_list_runs_finds_directories(tmp_runs):
    runs = list_runs(tmp_runs)
    assert len(runs) == 2
    names = {r.name for r in runs}
    assert names == {"run-alpha", "run-beta"}


def test_list_runs_returns_summaries(tmp_runs):
    runs = list_runs(tmp_runs)
    by_name = {r.name: r for r in runs}
    alpha = by_name["run-alpha"]
    assert alpha.risk_count == 3
    assert alpha.source_documents == ["policy.pdf"]


def test_list_runs_empty_dir(tmp_path):
    runs = list_runs(tmp_path)
    assert runs == []


def test_list_runs_skips_non_run_dirs(tmp_path):
    (tmp_path / "not-a-run").mkdir()
    (tmp_path / "not-a-run" / "random.txt").write_text("hello")
    runs = list_runs(tmp_path)
    assert runs == []


def test_load_run(tmp_runs):
    data = load_run(tmp_runs, "run-alpha")
    assert data["version"] == "0.3"
    assert len(data["risks"]) == 3
    assert data["risks"][0]["risk_id"] == "atlas-risk-0"


def test_load_run_not_found(tmp_runs):
    try:
        load_run(tmp_runs, "nonexistent")
        assert False, "Should have raised"
    except FileNotFoundError:
        pass


def test_load_category_map(tmp_sssom):
    cat_map = load_category_map(tmp_sssom)
    assert "atlas-risk-0" in cat_map
    assert "nist-ai-rmf" in cat_map["atlas-risk-0"]
    assert "nist-data-privacy" in cat_map["atlas-risk-0"]["nist-ai-rmf"]
    assert "ailuminate-v1.0" in cat_map["atlas-risk-0"]
    assert "ail-privacy" in cat_map["atlas-risk-0"]["ailuminate-v1.0"]


def test_load_category_map_excludes_related_match(tmp_sssom):
    cat_map = load_category_map(tmp_sssom)
    risk_1_ail = cat_map.get("atlas-risk-1", {}).get("ailuminate-v1.0", set())
    assert "ail-hate" not in risk_1_ail


def test_load_category_map_includes_close_match(tmp_sssom):
    cat_map = load_category_map(tmp_sssom)
    assert "nist-confabulation" in cat_map["atlas-risk-1"]["nist-ai-rmf"]


def test_list_policies(tmp_policies):
    policies = list_policies(tmp_policies)
    names = {p.name for p in policies}
    assert "banking-policy.md" in names
    assert "healthcare.json" in names
    assert "report.pdf" in names
    assert ".hidden" not in names


def test_list_policies_includes_subdirs(tmp_policies):
    policies = list_policies(tmp_policies)
    by_name = {p.name: p for p in policies}
    assert "multi-doc-group" in by_name
    assert by_name["multi-doc-group"].file_type == "directory"
