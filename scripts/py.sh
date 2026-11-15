#!/bin/sh

# Run Python portably for the git hooks (#229): use the first of python3, the
# Windows `py -3` launcher and python that is at least the minimum version.
# Every candidate is probed with arguments, so the Microsoft Store stub
# (WindowsApps\python3.exe), which only prints an install hint, is skipped.
# Keep `min_minor` in sync with python-version in
# .github/workflows/windows-hooks.yml; Ubuntu CI uses ubuntu-latest's python3.

set -u

min_major=3
min_minor=12
nl='
'
tried=""

for candidate in python3 "py -3" python; do
    if ! path="$(command -v "${candidate%% *}" 2>/dev/null)"; then
        tried="${tried}${nl}  ${candidate}: not on PATH"
        continue
    fi
    # shellcheck disable=SC2086 # split "py -3" into the command and its flag
    version="$(${candidate} -c 'import sys; sys.stdout.write("%d.%d" % sys.version_info[:2])' 2>/dev/null)"
    case "${version}" in
    *[!0-9.]* | *.*.*) version="" ;;
    *) ;;
    esac
    case "${version}" in
    [0-9]*.[0-9]*) ;;
    *)
        why="not a working interpreter"
        case "${path}" in
        *[Ww]indows[Aa]pps*) why="Microsoft Store stub, runs no code" ;;
        *) ;;
        esac
        tried="${tried}${nl}  ${candidate} (${path}): ${why}"
        continue
        ;;
    esac
    major="${version%%.*}"
    minor="${version#*.}"
    if [ "$((major * 1000 + minor))" -ge "$((min_major * 1000 + min_minor))" ]; then
        # shellcheck disable=SC2086 # see above
        exec ${candidate} "$@"
    fi
    tried="${tried}${nl}  ${candidate} (${path}): Python ${version}, too old"
done

# printf is a builtin, so this still prints when PATH has no coreutils.
printf '%s\n' "scripts/py.sh: no Python >= ${min_major}.${min_minor} found. Tried:${tried}" \
    "Install Python ${min_major}.${min_minor}+ from https://www.python.org/downloads/" \
    "(on Windows: \`winget install Python.Python.${min_major}.${min_minor}\`; the hooks find it via \`py -3\`)." >&2
exit 1
