#!/bin/bash

# Fail when INDEX.md or the README index block is stale against .apm/.
#
# Used by the Generate Index workflow on pull requests: instead of pushing a
# `[skip ci]` fix-up commit to the PR branch (which leaves required checks
# pending forever), the PR fails with instructions to regenerate locally.
# The working tree is left untouched; the would-be changes are printed as a diff.

set -euo pipefail

files=(INDEX.md README.md)
backup="$(mktemp -d)"

restore() {
    for f in "${files[@]}"; do
        if [ -f "${backup}/${f}" ]; then
            cp "${backup}/${f}" "${f}"
        else
            rm -f "${f}"
        fi
    done
    rm -rf "${backup}"
}

for f in "${files[@]}"; do
    if [ -f "${f}" ]; then
        cp "${f}" "${backup}/${f}"
    fi
done
trap restore EXIT

bash scripts/generate-index.sh >/dev/null

stale=()
for f in "${files[@]}"; do
    if [ ! -f "${backup}/${f}" ]; then
        stale+=("${f}")
        echo "--- ${f} is missing"
    elif ! diff -u --label "a/${f}" --label "b/${f}" "${backup}/${f}" "${f}"; then
        stale+=("${f}")
    fi
done

if [ "${#stale[@]}" -gt 0 ]; then
    msg="The primitive index is stale (${stale[*]}). Run 'bash scripts/generate-index.sh' and commit the result."
    if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
        echo "::error title=Stale primitive index::${msg}"
    fi
    echo "❌ ${msg}" >&2
    exit 1
fi

echo "✅ INDEX.md and the README index are up to date."
