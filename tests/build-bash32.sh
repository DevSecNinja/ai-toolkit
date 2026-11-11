#!/usr/bin/env bash
# Build Bash 3.2.57, the version stock macOS still runs for `#!/bin/bash`, so CI
# can run the hook scripts under it (see tests/test_hook_scripts.py).
#
# Usage: tests/build-bash32.sh [DEST_DIR]
# Prints the path of the built `bash`. Needs curl, a C compiler, make and bison.

set -euo pipefail

VERSION="3.2.57"
SHA256="3fa9daf85ebf35068f090ce51283ddeeb3c75eb5bc70b1a4a7cb05868bfe06a4"
DEST="${1:-${HOME}/.cache/bash-${VERSION}}"
# Anchor a relative DEST to the caller's directory; the build `cd`s away below.
case "${DEST}" in
/*) ;;
*) DEST="${PWD}/${DEST}" ;;
esac

if [[ -x "${DEST}/bash" ]]; then
    printf '%s\n' "${DEST}/bash"
    exit 0
fi

for tool in curl make bison; do
    command -v "${tool}" >/dev/null || {
        echo "build-bash32: ${tool} is required" >&2
        exit 1
    }
done

work="$(mktemp -d)"
trap 'rm -rf "${work}"' EXIT

curl -fsSL --retry 3 "https://ftpmirror.gnu.org/bash/bash-${VERSION}.tar.gz" -o "${work}/bash.tar.gz"
printf '%s  %s\n' "${SHA256}" "${work}/bash.tar.gz" | sha256sum -c - >/dev/null
tar -xzf "${work}/bash.tar.gz" -C "${work}"
cd "${work}/bash-${VERSION}"

# Bash 3.2 predates C99 and ships a stale y.tab.c: relax modern GCC's errors
# (via CC, so build-host helpers get them too) and regenerate the parser.
export CC="${CC:-gcc} -std=gnu89 -Wno-implicit-function-declaration -Wno-implicit-int -Wno-int-conversion -Wno-incompatible-pointer-types"
export YACC="bison -y"
./configure --quiet --without-bash-malloc >"${work}/configure.log" 2>&1 || {
    tail -n 40 "${work}/configure.log" >&2
    exit 1
}
jobs="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)"
make -j"${jobs}" >"${work}/make.log" 2>&1 || {
    tail -n 40 "${work}/make.log" >&2
    exit 1
}

mkdir -p "${DEST}"
cp bash "${DEST}/bash"
printf '%s\n' "${DEST}/bash"
