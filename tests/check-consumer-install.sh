#!/usr/bin/env bash
# Install this package into a throwaway consumer project, pinned to one commit,
# exactly as a consumer pinning a release tag would. Fails when the package's
# dependency graph cannot resolve (e.g. the self-dependency from #207).
#
# Usage: tests/check-consumer-install.sh <owner/repo> <commit-sha-or-ref>
# Needs the pinned `apm` CLI on PATH and GITHUB_TOKEN for the GitHub API.
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "usage: $0 <owner/repo> <commit-sha-or-ref>" >&2
    exit 2
fi

repo="$1"
ref="$2"
consumer="$(mktemp -d)"
trap 'rm -rf "${consumer}"' EXIT

cat >"${consumer}/apm.yml" <<EOF
name: consumer-install-check
version: 0.0.0
dependencies:
  apm:
    - ${repo}#${ref}
targets:
  - copilot
EOF

cd "${consumer}"
git init --quiet
apm --version
apm install --only apm
echo "Consumer install of ${repo}#${ref} resolved."
