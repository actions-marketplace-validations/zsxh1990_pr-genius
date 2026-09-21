#!/bin/bash
set -euo pipefail

# PR Genius GitHub Action Entry Point
# Supports both direct command and action inputs

# If args are provided, use them directly (for docker:// usage)
if [ $# -gt 0 ]; then
    exec python3 -m prgenius "$@"
fi

# Otherwise, use action inputs
if [ -z "${INPUT_TITLE:-}" ]; then
    echo "Error: title input is required"
    exit 1
fi

if [ -z "${INPUT_REPO:-}" ]; then
    echo "Error: repo input is required"
    exit 1
fi

# Build argument array (no eval — prevents shell injection)
ARGS=("python3" "-m" "prgenius" "${INPUT_COMMAND:-coach}")
ARGS+=("${INPUT_TITLE}")
ARGS+=("--repo" "${INPUT_REPO}")

if [ -n "${INPUT_BODY:-}" ]; then
    ARGS+=("--body" "${INPUT_BODY}")
fi

if [ -n "${INPUT_DESCRIPTION:-}" ]; then
    ARGS+=("--description" "${INPUT_DESCRIPTION}")
fi

if [ -n "${INPUT_FORMAT:-}" ]; then
    ARGS+=("--format" "${INPUT_FORMAT}")
fi

if [ -n "${INPUT_DIFF_STAT:-}" ]; then
    ARGS+=("--diff-stat" "${INPUT_DIFF_STAT}")
fi

if [ -n "${INPUT_AUTHOR:-}" ]; then
    ARGS+=("--author" "${INPUT_AUTHOR}")
fi

if [ -n "${INPUT_STAR_COUNT:-}" ]; then
    ARGS+=("--star-count" "${INPUT_STAR_COUNT}")
fi

if [ -n "${INPUT_REPO_MERGE_RATE:-}" ]; then
    ARGS+=("--repo-merge-rate" "${INPUT_REPO_MERGE_RATE}")
fi

# Execute — no eval, arguments are passed as an array
echo "Running: ${ARGS[*]}"
exec "${ARGS[@]}"
