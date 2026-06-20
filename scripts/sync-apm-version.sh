#!/bin/bash

# Sync the APM manifest (apm.yml) version with a GitHub release tag.
#
# APM resolves the package version from the `version:` field in apm.yml. This
# script updates that field to match a published GitHub release so the APM
# package version always tracks the repository's releases.
#
# Usage:
#   bash scripts/sync-apm-version.sh <version>
#   bash scripts/sync-apm-version.sh v1.2.3   # a leading "v" is stripped

set -euo pipefail

MANIFEST="apm.yml"

raw_version="${1:-}"
if [ -z "$raw_version" ]; then
  echo "❌ Usage: $0 <version>" >&2
  exit 1
fi

# Strip a leading "v" (v1.2.3 -> 1.2.3) so the manifest holds a bare semver.
version="${raw_version#v}"

if [ ! -f "$MANIFEST" ]; then
  echo "❌ $MANIFEST not found" >&2
  exit 1
fi

if ! grep -qE '^version:' "$MANIFEST"; then
  echo "❌ No 'version:' field found in $MANIFEST" >&2
  exit 1
fi

# Replace the version line in place.
sed -i -E "s/^version:.*/version: ${version}/" "$MANIFEST"

echo "✅ Set ${MANIFEST} version to ${version}"
