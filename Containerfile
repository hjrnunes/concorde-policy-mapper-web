FROM python:3.12-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/IBM/ai-atlas-nexus.git /opt/nexus
RUN pip install --no-cache-dir /opt/nexus

WORKDIR /app

COPY --from=concorde-policy-mapper src /deps/concorde-policy-mapper/src
COPY --from=concorde-policy-mapper data /deps/concorde-policy-mapper/data
COPY --from=concorde-policy-mapper pyproject.toml /deps/concorde-policy-mapper/
RUN pip install --no-cache-dir --no-deps /deps/concorde-policy-mapper
RUN pip install --no-cache-dir instructor openai pydantic typer pyyaml jinja2 docling "torch>=2.11,<2.12" "transformers>=5.5,<5.6" sentence-transformers rank-bm25 nltk numpy mlflow pylate

COPY --from=concorde-policy-mapper policy_examples /app/policy_examples

COPY . .
RUN pip install --no-cache-dir --no-deps .
RUN pip install --no-cache-dir fastapi 'uvicorn[standard]' python-multipart

RUN mkdir -p /app/runs /app/runs/_uploads /tmp/pystow && \
    chmod -R 777 /app/runs /tmp/pystow

ENV HOME=/tmp
ENV PYSTOW_HOME=/tmp/pystow
ENV NEXUS_BASE_DIR=/opt/nexus
ENV RUNS_DIR=/app/runs
ENV EXAMPLES_DIR=/app/policy_examples

EXPOSE 8080
CMD ["uvicorn", "concorde_policy_mapper_web.app:app", "--host", "0.0.0.0", "--port", "8080"]
