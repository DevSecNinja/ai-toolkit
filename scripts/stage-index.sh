#!/bin/bash

# Pre-commit: regenerate INDEX.md and the README index from the STAGED tree and
# stage only the result. Unstaged README prose and untracked or unstaged
# primitives never leak into the commit, and deletions are covered too, so the
# committed index matches what CI's check-index.sh regenerates (#219).
# The working tree is regenerated separately to reflect its own primitives.

set -euo pipefail

relevant='^(\.apm/|\.github/prompts/|\.github/agents/|INDEX\.md$|README\.md$|scripts/generate-index\.sh$)'
if ! git diff --cached --name-only --no-renames | grep -Eq "${relevant}"; then
    exit 0
fi

snapshot="$(mktemp -d)"
trap 'rm -rf "${snapshot}"' EXIT

git checkout-index --all --prefix="${snapshot}/"
(cd "${snapshot}" && bash scripts/generate-index.sh >/dev/null)

for f in INDEX.md README.md; do
    blob="$(git hash-object -w --path="${f}" "${snapshot}/${f}")"
    if [ "${blob}" != "$(git rev-parse -q --verify ":${f}" || true)" ]; then
        git update-index --add --cacheinfo "100644,${blob},${f}"
        echo "📑 Staged regenerated ${f}"
    fi
done

bash scripts/generate-index.sh >/dev/null
