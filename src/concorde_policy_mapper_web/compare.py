from collections import Counter


def build_comparison(runs: list[dict]) -> dict:
    risk_to_runs: dict[str, list[str]] = {}
    risk_info: dict[str, dict] = {}
    per_run_data: dict[str, dict[str, dict]] = {}

    for run in runs:
        name = run["name"]
        per_run_data[name] = {}
        for risk in run["data"].get("risks", []):
            rid = risk["risk_id"]
            risk_to_runs.setdefault(rid, []).append(name)
            risk_info.setdefault(rid, {
                "risk_id": rid,
                "risk_name": risk.get("risk_name", rid),
                "taxonomy": risk.get("taxonomy", ""),
            })
            per_run_data[name][rid] = {
                "confidence": risk.get("confidence", 0),
                "grounding_confidence": risk.get("grounding_confidence", ""),
                "evidence_count": len(risk.get("evidence", [])),
                "mitigation_count": len(risk.get("mitigations", [])),
            }

    run_names = [r["name"] for r in runs]
    run_set = set(run_names)

    shared_risks = []
    unique_risks = {name: [] for name in run_names}

    for rid, present_in in sorted(risk_to_runs.items(), key=lambda x: (-len(x[1]), x[0])):
        present_set = set(present_in)
        info = dict(risk_info[rid])
        info["per_run"] = {
            name: per_run_data[name][rid]
            for name in run_names
            if rid in per_run_data[name]
        }
        if present_set == run_set:
            shared_risks.append(info)
        else:
            for name in present_in:
                if len(present_set) < len(run_set):
                    unique_risks[name].append(info)

    summaries = []
    for run in runs:
        risks = run["data"].get("risks", [])
        metadata = run["data"].get("metadata", {})
        summaries.append({
            "name": run["name"],
            "risk_count": len(risks),
            "model": metadata.get("model", ""),
            "source_documents": [
                p.rsplit("/", 1)[-1]
                for p in run["data"].get("source_documents", [])
            ],
        })

    return {
        "summaries": summaries,
        "shared_risks": shared_risks,
        "unique_risks": unique_risks,
        "run_names": run_names,
    }
