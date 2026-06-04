# Concorde Policy Mapper Web

Web UI for browsing and launching [concorde-policy-mapper](../concorde-policy-mapper) risk extractions.

## What it does

- **Browse extraction runs** — lists completed runs with risk counts and source documents
- **Taxonomy-grouped risk views** — risks grouped by NIST AI RMF, OWASP LLM, AILuminate, or OWASP ASI categories, with an "All Risks" flat view and uncategorized bucket per taxonomy
- **Risk detail pages** — causal chain visualization (threat source → threat → vulnerability → consequence → impact), evidence spans with source quotes, and mitigations filterable by DPV risk control type and category (technical/operational/governance)
- **Run comparison** — side-by-side risk overlap, shared risks with confidence comparison, unique risks per run
- **Launch new extractions** — select a bundled policy example or upload a document, configure LLM endpoint, stream progress via SSE

## Stack

- **Backend**: FastAPI + Uvicorn + Jinja2, Python 3.11+
- **Frontend**: Tailwind CSS (CDN) + Alpine.js (CDN), server-rendered HTML, no build step
- **CLI dependency**: `concorde-policy-mapper` (sibling directory)

## Local Development

```bash
# Install both packages
uv pip install -e ../concorde-policy-mapper
uv pip install -e ".[dev]"

# Run tests
uv run python -m pytest tests/ -v

# Start dev server pointing at existing extraction runs
RUNS_DIR=../concorde-policy-mapper/extract-runs/risk-selected_20260603_143331 \
  uv run concorde-policy-mapper-web
```

Open http://localhost:8080.

### Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `RUNS_DIR` | Directory containing extraction run outputs | `runs` |
| `EXAMPLES_DIR` | Directory with bundled policy examples | `policy_examples` |
| `MODEL_BASE_URL` | LLM API endpoint (OpenAI-compatible) | — |
| `MODEL_NAME` | Model identifier | — |
| `MODEL_API_KEY` | LLM authentication key | `none` |
| `NEXUS_BASE_DIR` | Path to ai-atlas-nexus repo checkout | — |
| `PORT` | Server listen port | `8080` |

## Deployment (OpenShift)

The app deploys to OpenShift via binary build — no local container runtime needed.

### Prerequisites

- `oc` CLI logged into the cluster
- `concorde-policy-mapper` source at `../concorde-policy-mapper` (or set `POLICY_MAPPER_DIR`)

### First-time setup

```bash
# Create project
oc new-project concorde-policy-mapper-web

# Create BuildConfig and ImageStream
oc create imagestream concorde-policy-mapper-web

oc create -f - <<'EOF'
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: concorde-policy-mapper-web
  labels:
    app: concorde-policy-mapper-web
spec:
  output:
    to:
      kind: ImageStreamTag
      name: concorde-policy-mapper-web:latest
  source:
    type: Binary
  strategy:
    type: Docker
    dockerStrategy:
      dockerfilePath: Containerfile
  resources:
    limits:
      cpu: "1"
      memory: 2Gi
EOF

# Build and push image
bash scripts/oc-build.sh

# Deploy
oc apply -f openshift/

# (Optional) Create API key secret if your LLM endpoint requires auth
oc create secret generic concorde-policy-mapper-web --from-literal=api-key=<key>
```

### Rebuilding after code changes

```bash
bash scripts/oc-build.sh
oc rollout restart deployment/concorde-policy-mapper-web
```

The build script (`scripts/oc-build.sh`) assembles both `concorde-policy-mapper` and `concorde-policy-mapper-web` sources into a single build context, uploads it, and triggers an on-cluster build. Builds take ~15 minutes (mostly downloading torch/CUDA dependencies).

### Current deployment

- **Cluster**: `api.u1q6z7t9c5c9x9t.262f.p3.openshiftapps.com`
- **Namespace**: `concorde-policy-mapper-web`
- **Route**: https://concorde-policy-mapper-web-concorde-policy-mapper-web.apps.rosa.u1q6z7t9c5c9x9t.262f.p3.openshiftapps.com
- **Model**: `gemma-4-26b-a4b-it` via vLLM on the same cluster

## Lessons Learned / Known Issues

### Container data path resolution

`concorde-policy-mapper` resolves its data files (mitigations index, threat/consequence YAML, SSSOM taxonomy mapping) via `Path(__file__).resolve().parents[3] / "data"`. When pip-installed in a container, `__file__` is under `/usr/local/lib/python3.12/site-packages/`, so `parents[3]` resolves to `/usr/local/lib/python3.12/` — not where the data files actually are.

**Fix**: The Containerfile creates a symlink: `ln -s /deps/concorde-policy-mapper/data /usr/local/lib/python3.12/data`. This makes both the CLI and the web app find the data files without code changes to concorde-policy-mapper.

### ai-atlas-nexus version pinning

The Containerfile must pin `ai-atlas-nexus` to the same commit that `concorde-policy-mapper` depends on (currently `30f29c3b`). Latest main has breaking changes in Pydantic adapter type validation (iterates string characters instead of treating the string as an enum value).

### Memory requirements

The extraction subprocess loads sentence-transformers and cross-encoder ML models (~4GB RSS). The container needs **at least 6Gi memory limit** — at 2Gi and 4Gi the subprocess is OOM-killed mid-extraction (exit code 137), producing empty output directories and "Lost connection" errors in the browser.

### System dependencies for docling

The `python:3.12-slim` base image is missing `libGL` and `libglib2.0` which OpenCV (a docling transitive dependency) requires at runtime. Install with: `apt-get install -y libgl1 libglib2.0-0`.

### SSSOM taxonomy mapping

The `risk_to_category.sssom.tsv` file has blank lines between the comment header and the data header row. The CSV parser must skip both comment lines (`#` prefix) and empty lines, otherwise the blank line is treated as the header row and all data parsing fails silently (empty category map, all taxonomy tab counts show 0).

### Jinja2 auto-escaping in JavaScript

JSON data passed to Jinja2 templates and used in `<script>` blocks must use the `|safe` filter. Without it, Jinja2 HTML-escapes the JSON (`"` becomes `&#34;`), producing invalid JavaScript. Alpine.js silently fails to parse the data and renders nothing. Symptom: the section header shows the correct count (e.g. "189 actions") but no items render below the filter buttons.

### Token usage field naming

The `token_usage` dict from `concorde-policy-mapper` uses `total_tokens` as the key (not `total`). Templates should use `data.token_usage.total_tokens`.

### Build resource limits

The OpenShift BuildConfig needs at least 1 CPU and 2Gi memory. The default 4 CPU / 8Gi may exceed cluster capacity and cause builds to hang in `Pending` state. The build downloads ~2GB of Python wheels (torch, CUDA, transformers) so it takes ~15 minutes even with adequate resources.

### OpenShift route timeout

The route annotation `haproxy.router.openshift.io/timeout: 10m` is essential — extractions typically take 5-10 minutes. Without it, the HAProxy default (30s) kills the SSE connection mid-extraction.
