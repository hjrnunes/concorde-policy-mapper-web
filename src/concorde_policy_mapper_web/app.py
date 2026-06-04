import json
import os
import subprocess
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from concorde_policy_mapper_web import scanner
from concorde_policy_mapper_web.scanner import (
    TAXONOMY_DISPLAY,
    category_display_name,
    group_risks_by_taxonomy,
)

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"


def _build_category_tags(
    risk_id: str,
    category_map: dict[str, dict[str, set[str]]],
) -> list[dict[str, str]]:
    tags = []
    for tax_key, tax_label in TAXONOMY_DISPLAY.items():
        cats = category_map.get(risk_id, {}).get(tax_key, set())
        for cat_id in sorted(cats):
            tags.append({"taxonomy": tax_label, "category": category_display_name(cat_id)})
    return tags


def _find_sssom_path() -> Path | None:
    _SSSOM = "risk_to_category.sssom.tsv"
    try:
        import concorde_policy_mapper.extract.mitigations as _m
        # Use the same parents[3] / "data" path the CLI uses for its own data files
        candidate = Path(_m.__file__).resolve().parents[3] / "data" / _SSSOM
        if candidate.exists():
            return candidate
    except ImportError:
        pass
    local = Path("data") / _SSSOM
    if local.exists():
        return local
    sibling = Path(__file__).resolve().parent.parent.parent.parent / "concorde-policy-mapper" / "data" / _SSSOM
    if sibling.exists():
        return sibling
    return None


def create_app(
    runs_dir: Path | None = None,
    examples_dir: Path | None = None,
) -> FastAPI:
    runs_dir = runs_dir or Path(os.environ.get("RUNS_DIR", "runs"))
    examples_dir = examples_dir or Path(os.environ.get("EXAMPLES_DIR", "policy_examples"))

    app = FastAPI(title="Concorde Policy Mapper Web")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    sssom_path = _find_sssom_path()
    category_map = scanner.load_category_map(sssom_path) if sssom_path else {}

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        runs = scanner.list_runs(runs_dir)
        return templates.TemplateResponse(
            request=request,
            name="runs.html",
            context={"runs": runs, "active_run": None},
        )

    @app.get("/runs/{name}", response_class=HTMLResponse)
    async def run_detail(request: Request, name: str):
        try:
            data = scanner.load_run(runs_dir, name)
        except FileNotFoundError:
            return JSONResponse(status_code=404, content={"detail": f"Run '{name}' not found"})

        runs = scanner.list_runs(runs_dir)
        risks = data.get("risks", [])
        risks_sorted = sorted(risks, key=lambda r: r.get("confidence", 0), reverse=True)

        taxonomy_groups = {}
        for tax_key, tax_label in TAXONOMY_DISPLAY.items():
            groups, uncategorized = group_risks_by_taxonomy(risks_sorted, category_map, tax_key)
            display_groups = {
                category_display_name(cat_id): cat_risks
                for cat_id, cat_risks in sorted(groups.items())
            }
            mapped_count = sum(len(v) for v in groups.values())
            taxonomy_groups[tax_key] = {
                "label": tax_label,
                "groups": display_groups,
                "uncategorized": uncategorized,
                "mapped_count": mapped_count,
            }

        risk_categories = {
            risk["risk_id"]: _build_category_tags(risk["risk_id"], category_map)
            for risk in risks
        }

        return templates.TemplateResponse(
            request=request,
            name="run_detail.html",
            context={
                "runs": runs,
                "active_run": name,
                "run_name": name,
                "data": data,
                "risks": risks_sorted,
                "risks_json": json.dumps(risks_sorted),
                "taxonomy_groups": taxonomy_groups,
                "taxonomy_groups_json": json.dumps(
                    {k: {"label": v["label"], "mapped_count": v["mapped_count"]}
                     for k, v in taxonomy_groups.items()}
                ),
                "risk_categories_json": json.dumps(risk_categories),
            },
        )

    @app.get("/runs/{name}/risk/{risk_id}", response_class=HTMLResponse)
    async def risk_detail(request: Request, name: str, risk_id: str):
        try:
            data = scanner.load_run(runs_dir, name)
        except FileNotFoundError:
            return JSONResponse(status_code=404, content={"detail": f"Run '{name}' not found"})
        risk = next((r for r in data.get("risks", []) if r["risk_id"] == risk_id), None)
        if risk is None:
            return JSONResponse(status_code=404, content={"detail": f"Risk '{risk_id}' not found"})

        category_tags = _build_category_tags(risk_id, category_map)

        runs = scanner.list_runs(runs_dir)
        return templates.TemplateResponse(
            request=request,
            name="risk_detail.html",
            context={
                "runs": runs,
                "active_run": name,
                "run_name": name,
                "risk": risk,
                "risk_json": json.dumps(risk),
                "category_tags": category_tags,
            },
        )

    @app.get("/compare", response_class=HTMLResponse)
    async def compare_view(request: Request, runs: str = ""):
        run_names = [n.strip() for n in runs.split(",") if n.strip()]
        if len(run_names) < 2:
            return JSONResponse(status_code=400, content={"detail": "At least 2 runs required"})

        from concorde_policy_mapper_web.compare import build_comparison

        inputs = []
        for rname in run_names:
            try:
                data = scanner.load_run(runs_dir, rname)
            except FileNotFoundError:
                return JSONResponse(status_code=404, content={"detail": f"Run '{rname}' not found"})
            inputs.append({"name": rname, "data": data})

        comparison = build_comparison(inputs)
        all_runs = scanner.list_runs(runs_dir)
        return templates.TemplateResponse(
            request=request,
            name="compare.html",
            context={
                "runs": all_runs,
                "active_run": None,
                "comparison": comparison,
            },
        )

    active_runs: dict[str, subprocess.Popen] = {}

    @app.get("/run", response_class=HTMLResponse)
    async def new_run_page(request: Request):
        policies = scanner.list_policies(examples_dir)
        all_runs = scanner.list_runs(runs_dir)
        return templates.TemplateResponse(
            request=request,
            name="new_run.html",
            context={
                "runs": all_runs,
                "active_run": None,
                "policies": policies,
                "env_base_url": os.environ.get("MODEL_BASE_URL", ""),
                "env_model": os.environ.get("MODEL_NAME", ""),
                "env_api_key": os.environ.get("MODEL_API_KEY", "none"),
            },
        )

    @app.post("/run")
    async def start_run_endpoint(
        source_type: str = Form(...),
        base_url: str = Form(...),
        model: str = Form(...),
        api_key: str = Form("none"),
        example_name: str = Form(None),
        file: UploadFile = File(None),
    ):
        from concorde_policy_mapper_web import runner

        if source_type == "example" and example_name:
            policy_path = examples_dir / example_name
            if not policy_path.exists():
                return JSONResponse(status_code=400, content={"detail": f"Example '{example_name}' not found"})
            run_id = runner.generate_run_id(example_name)
        elif source_type == "upload" and file:
            safe_name = Path(file.filename).name if file.filename else ""
            if not safe_name:
                return JSONResponse(status_code=400, content={"detail": "Invalid filename"})
            upload_dir = runs_dir / "_uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            policy_path = upload_dir / safe_name
            content = await file.read()
            policy_path.write_bytes(content)
            run_id = runner.generate_run_id(safe_name)
        else:
            return JSONResponse(status_code=400, content={"detail": "No policy source provided"})

        output_dir = runs_dir / run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        process = runner.start_run(
            policy_path=policy_path,
            output_dir=output_dir,
            base_url=base_url,
            model=model,
            api_key=api_key,
            nexus_base_dir=os.environ.get("NEXUS_BASE_DIR"),
        )
        active_runs[run_id] = process
        return {"run_id": run_id}

    @app.get("/run/stream/{run_id}")
    async def run_stream(run_id: str):
        from concorde_policy_mapper_web import runner

        process = active_runs.get(run_id)
        if process is None:
            return JSONResponse(status_code=404, content={"detail": f"Run '{run_id}' not found"})

        def cleanup_generator():
            try:
                yield from runner.stream_progress(process, run_id)
            finally:
                active_runs.pop(run_id, None)
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()

        return StreamingResponse(cleanup_generator(), media_type="text/event-stream")

    app.state.runs_dir = runs_dir
    app.state.examples_dir = examples_dir
    app.state.templates = templates

    return app


app = create_app()


def cli():
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(
        "concorde_policy_mapper_web.app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
