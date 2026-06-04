FROM python:3.12-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=concorde-policy-mapper src /deps/concorde-policy-mapper/src
COPY --from=concorde-policy-mapper data /deps/concorde-policy-mapper/data
COPY --from=concorde-policy-mapper pyproject.toml /deps/concorde-policy-mapper/
RUN pip install --no-cache-dir /deps/concorde-policy-mapper

COPY . .
RUN pip install --no-cache-dir .

RUN mkdir -p /app/runs /app/runs/_uploads && chmod -R 777 /app/runs

ENV HOME=/tmp
ENV RUNS_DIR=/app/runs
ENV EXAMPLES_DIR=/app/policy_examples

EXPOSE 8080
CMD ["uvicorn", "concorde_policy_mapper_web.app:app", "--host", "0.0.0.0", "--port", "8080"]
