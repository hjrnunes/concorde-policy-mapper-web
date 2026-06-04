#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WEB_DIR="$(dirname "$SCRIPT_DIR")"
MAPPER_DIR="${POLICY_MAPPER_DIR:-$(dirname "$WEB_DIR")/concorde-policy-mapper}"

if [ ! -d "$MAPPER_DIR/src" ]; then
  echo "Error: concorde-policy-mapper not found at $MAPPER_DIR"
  echo "Set POLICY_MAPPER_DIR to override"
  exit 1
fi

BUILD_DIR=$(mktemp -d)
trap 'rm -rf "$BUILD_DIR"' EXIT

echo "Assembling build context..."
mkdir -p "$BUILD_DIR/_deps/concorde-policy-mapper"
cp -r "$MAPPER_DIR/src" "$BUILD_DIR/_deps/concorde-policy-mapper/"
cp -r "$MAPPER_DIR/data" "$BUILD_DIR/_deps/concorde-policy-mapper/"
cp "$MAPPER_DIR/pyproject.toml" "$BUILD_DIR/_deps/concorde-policy-mapper/"
cp -r "$MAPPER_DIR/policy_examples" "$BUILD_DIR/_deps/concorde-policy-mapper/"

mkdir -p "$BUILD_DIR/web"
cp -r "$WEB_DIR/src" "$BUILD_DIR/web/"
cp "$WEB_DIR/pyproject.toml" "$BUILD_DIR/web/"

cp "$WEB_DIR/Containerfile.openshift" "$BUILD_DIR/Containerfile"

echo "Starting OpenShift build..."
oc start-build concorde-policy-mapper-web \
  --from-dir="$BUILD_DIR" \
  --follow
