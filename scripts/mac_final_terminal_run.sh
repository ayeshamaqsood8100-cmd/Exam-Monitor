#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

if [[ ! -d ".venv" ]]; then
    echo "Missing .venv in $REPO_ROOT"
    exit 1
fi

if [[ -z "${BACKEND_URL:-}" || -z "${BACKEND_API_KEY:-}" || -z "${EXAM_ID:-}" ]]; then
    echo "BACKEND_URL, BACKEND_API_KEY, and EXAM_ID must already be exported."
    echo "Reuse the same values from the previous Mac test session before running this script."
    exit 1
fi

source ".venv/bin/activate"

echo "== Markaz macOS final terminal run =="
echo "Repo: $REPO_ROOT"
echo

echo "Installing macOS-specific Python requirements..."
python -m pip install -r agent/requirements_mac.txt

echo
echo "Running macOS setup checks..."
python -m agent.setup_mac

echo
echo "Starting the agent directly through agent.main..."
echo "Use watchdog only after this pass succeeds."
python -m agent.main
