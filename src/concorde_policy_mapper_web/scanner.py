import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

POLICY_EXTENSIONS = {".json", ".md", ".txt", ".pdf", ".docx", ".html", ".htm"}
STRONG_PREDICATES = {"skos:exactMatch", "skos:closeMatch", "skos:broadMatch"}

TAXONOMY_DISPLAY = {
    "nist-ai-rmf": "NIST AI RMF",
    "owasp-llm-2.0": "OWASP LLM",
    "ailuminate-v1.0": "AILuminate",
    "owasp-asi": "OWASP ASI",
}


@dataclass
class RunSummary:
    name: str
    risk_count: int
    source_documents: list[str]
    timestamp: str
    model: str
    path: Path


@dataclass
class PolicyInfo:
    name: str
    path: Path
    file_type: str


def list_runs(runs_dir: Path) -> list[RunSummary]:
    summaries = []
    if not runs_dir.is_dir():
        return summaries
    for d in sorted(runs_dir.iterdir()):
        if not d.is_dir():
            continue
        extraction_path = d / "risk-extraction.json"
        if not extraction_path.exists():
            continue
        data = json.loads(extraction_path.read_text())
        docs = data.get("source_documents", [])
        doc_names = [Path(p).name for p in docs]
        metadata = data.get("metadata", {})
        summaries.append(RunSummary(
            name=d.name,
            risk_count=len(data.get("risks", [])),
            source_documents=doc_names,
            timestamp=metadata.get("timestamp", ""),
            model=metadata.get("model", ""),
            path=d,
        ))
    return summaries


def load_run(runs_dir: Path, name: str) -> dict:
    d = runs_dir / name
    extraction_path = d / "risk-extraction.json"
    if not extraction_path.exists():
        raise FileNotFoundError(f"Run '{name}' not found at {d}")
    return json.loads(extraction_path.read_text())


def load_category_map(sssom_path: Path) -> dict[str, dict[str, set[str]]]:
    result: dict[str, dict[str, set[str]]] = {}
    with open(sssom_path) as f:
        reader = csv.DictReader(
            (line for line in f if not line.startswith("#") and line.strip()),
            delimiter="\t",
        )
        for row in reader:
            predicate = row.get("predicate_id", "")
            if predicate not in STRONG_PREDICATES:
                continue
            subject_id = row["subject_id"]
            object_id = row["object_id"]
            object_source = row["object_source"]
            result.setdefault(subject_id, {}).setdefault(object_source, set()).add(object_id)
    return result


def category_display_name(category_id: str) -> str:
    parts = category_id.split("-")
    for i, prefix in enumerate(parts):
        if prefix.isalpha() and len(prefix) <= 5:
            continue
        return " ".join(p.capitalize() for p in parts[i:])
    return " ".join(p.capitalize() for p in parts)


def group_risks_by_taxonomy(
    risks: list[dict],
    category_map: dict[str, dict[str, set[str]]],
    taxonomy: str,
) -> tuple[dict[str, list[dict]], list[dict]]:
    groups: dict[str, list[dict]] = {}
    uncategorized = []
    for risk in risks:
        risk_id = risk["risk_id"]
        categories = category_map.get(risk_id, {}).get(taxonomy, set())
        if not categories:
            uncategorized.append(risk)
        else:
            for cat_id in sorted(categories):
                groups.setdefault(cat_id, []).append(risk)
    return groups, uncategorized


def list_policies(examples_dir: Path) -> list[PolicyInfo]:
    policies = []
    if not examples_dir.is_dir():
        return policies
    for entry in sorted(examples_dir.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            policies.append(PolicyInfo(
                name=entry.name,
                path=entry,
                file_type="directory",
            ))
        elif entry.suffix.lower() in POLICY_EXTENSIONS:
            policies.append(PolicyInfo(
                name=entry.name,
                path=entry,
                file_type=entry.suffix.lower(),
            ))
    return policies
