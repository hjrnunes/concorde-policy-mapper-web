import re
from concorde_policy_mapper_web.runner import generate_run_id, parse_cli_line


def test_generate_run_id_format():
    run_id = generate_run_id("banking-policy.md")
    assert run_id.startswith("banking-policy-")
    assert re.match(r"banking-policy-\d{4}-\d{2}-\d{2}T\d{6}", run_id)


def test_generate_run_id_strips_extension():
    run_id = generate_run_id("my-doc.pdf")
    assert run_id.startswith("my-doc-")


def test_parse_cli_line_extract():
    event = parse_cli_line("Extracting risks from 2 document(s) (524 Nexus risks loaded)...")
    assert event is not None
    assert event["stage"] == "extract"


def test_parse_cli_line_mitigations():
    event = parse_cli_line("  Mitigations attached from 83 risk entries")
    assert event is not None
    assert event["stage"] == "mitigations"


def test_parse_cli_line_results():
    event = parse_cli_line("Risk extraction written to /app/runs/test/risk-extraction.json")
    assert event is not None
    assert event["stage"] == "results"


def test_parse_cli_line_report():
    event = parse_cli_line("Report written to /app/runs/test/risk-extraction.html")
    assert event is not None
    assert event["stage"] == "report"


def test_parse_cli_line_irrelevant():
    event = parse_cli_line("  3 auto-accepted, 2 LLM-judged")
    assert event is None


def test_parse_cli_line_empty():
    event = parse_cli_line("")
    assert event is None
