#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=== Initializing Standalone MCP Evaluation ==="

# Dynamically change to the directory where this bash script lives
cd "$(dirname "$0")"
echo "[Setup] Running workspace in: $(pwd)"

# Locate the CLI, install if missing
GEMINI_CLI="$(which gemini)"
if [ -z "$GEMINI_CLI" ]; then
  echo "Installing @google/gemini-cli globally..."
  npm install -g @google/gemini-cli
  GEMINI_CLI="$(which gemini)"
fi

echo "[Setup] Checking for python dependencies..."
pip3 install absl-py pydash --quiet

echo "--------------------------------------------------------"
echo "Running the Evaluation Engine..."

# Execute the raw Python script pointing to the local gce_1p.json
python3 mcpeval.py \
  --golden_prompts_responses="./gce_1p.json" \
  --gemini_cli_path="$GEMINI_CLI" \
  --context="Do not use gcloud or shell commands. Use the MCP servers." \
  --remotemcpjson='"google-compute-mcp": { "httpUrl": "https://compute.googleapis.com/mcp", "authProviderType": "google_credentials", "oauth": { "scopes": [ "https://www.googleapis.com/auth/compute.readonly" ] }, "trust": true, "timeout": 60000 }' \
  --remotemcpjson='"google-logging-mcp": { "httpUrl": "https://logging.googleapis.com/mcp", "authProviderType": "google_credentials", "oauth": { "scopes": [ "https://www.googleapis.com/auth/logging.read" ] }, "trust": true, "timeout": 60000 }' \
  --google_account=True

echo "--------------------------------------------------------"
echo "=== Evaluation Complete ==="