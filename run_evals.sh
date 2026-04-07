#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=== Initializing Standalone MCP Evaluation ==="

# 1. Define absolute paths based on the script living in the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
EVAL_DIR="${PROJECT_ROOT}/evals"
TEST_JSON="${EVAL_DIR}/test_data/gce_1p.json"

# We assume the user has the Gemini CLI installed globally via npm in Cloud Shell
GEMINI_CLI="$(which gemini)"

if [ -z "$GEMINI_CLI" ]; then
  echo "Error: Gemini CLI not found. Please install it first: npm i -g @google/gemini-cli"
  exit 1
fi

echo "[Setup] Checking for python dependencies..."
# Install the missing Google-like flag parser and pydash for dict comparisons
pip3 install absl-py pydash --quiet

echo "[Setup] Running evaluation from directory: $EVAL_DIR"
echo "--------------------------------------------------------"

# 2. Change into the evals directory so GEMINI.md and .gemini are created there
cd "$EVAL_DIR"

# 3. Execute the raw Python script
python3 mcpeval.py \
  --golden_prompts_responses="$TEST_JSON" \
  --gemini_cli_path="$GEMINI_CLI" \
  --context="Do not use gcloud or shell commands for information GCE VM instances, reservations and their status. Use the GCE MCP server instead" \
  --remotemcpjson='"google-compute-mcp": { "httpUrl": "https://compute.googleapis.com/mcp", "authProviderType": "google_credentials", "oauth": { "scopes": [ "https://www.googleapis.com/auth/compute.readonly" ] }, "trust": true,  "timeout": 60000 }' \
  --google_account=True

echo "--------------------------------------------------------"
echo "=== Evaluation Complete ==="