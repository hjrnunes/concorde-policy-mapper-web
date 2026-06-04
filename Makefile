POLICY_MAPPER_DIR ?= ../concorde-policy-mapper
NEXUS_BASE_DIR ?= ../ai-atlas-nexus

.PHONY: install image

install:
	uv pip install -e $(POLICY_MAPPER_DIR)
	uv pip install -e .

image:
	podman build --platform linux/amd64 --build-context concorde-policy-mapper=$(POLICY_MAPPER_DIR) -f Containerfile -t concorde-policy-mapper-web .
