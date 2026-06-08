import json
import os
import select
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def generate_run_id(filename: str) -> str:
    stem = Path(filename).stem
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    return f"{stem}-{ts}"


def parse_cli_line(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None
    if line.startswith("Extracting risks from"):
        return {"stage": "extract", "message": line}
    if "Mitigations attached" in line:
        return {"stage": "mitigations", "message": line}
    if line.startswith("Risk extraction written"):
        return {"stage": "results", "message": line}
    if line.startswith("Report written"):
        return {"stage": "report", "message": line}
    return None


def start_run(
    policy_path: Path,
    output_dir: Path,
    base_url: str,
    model: str,
    api_key: str = "none",
    nexus_base_dir: str | None = None,
) -> subprocess.Popen:
    cmd = [
        "concorde-policy-mapper", "extract",
        str(policy_path),
        "--output", str(output_dir),
        "--base-url", base_url,
        "--model", model,
        "--bi-encoder-model", os.environ.get("BI_ENCODER_MODEL_URL", ""),
        "--cross-encoder-model", os.environ.get("CROSS_ENCODER_MODEL_URL", ""),
        "--grounding-passes", "3",
        "--expansion-passes", "3",
        "--expand-siblings",
    ]
    if nexus_base_dir:
        cmd.extend(["--nexus-base-dir", nexus_base_dir])

    env = os.environ.copy()
    env["MODEL_API_KEY"] = api_key

    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )


def stream_progress(process: subprocess.Popen, run_name: str):
    tail_lines: list[str] = []
    fd = process.stdout.fileno()

    while True:
        ready, _, _ = select.select([fd], [], [], 10.0)
        if ready:
            line = process.stdout.readline()
            if not line:
                break
            event = parse_cli_line(line)
            if event:
                if event["stage"] == "report":
                    yield f"event: done\ndata: {json.dumps({'run_name': run_name, 'redirect': f'/runs/{run_name}'})}\n\n"
                else:
                    yield f"event: stage\ndata: {json.dumps(event)}\n\n"
            else:
                stripped = line.strip()
                if stripped:
                    tail_lines.append(stripped)
                    tail_lines = tail_lines[-20:]
        else:
            yield ": keepalive\n\n"

    process.wait()
    if process.returncode != 0:
        detail = "\n".join(tail_lines) if tail_lines else f"exit code {process.returncode}"
        yield f"event: pipeline_error\ndata: {json.dumps({'message': f'Pipeline failed: {detail}'})}\n\n"
