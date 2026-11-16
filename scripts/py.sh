#!/bin/sh

# Run Python portably for the git hooks (#229, #246). The version is the
# major.minor in the repo's .python-version, which mise installs (.mise.toml)
# and CI sets up. Use mise's Python for it, else the first of python3, the
# Windows `py -3` launcher and python that is at least that version. Every
# candidate is probed with arguments, so the Microsoft Store stub
# (WindowsApps\python3.exe), which only prints an install hint, is skipped.
# Only shell builtins are used, so this works even when PATH has no coreutils.

set -u

dir="${0%/*}"
[ "${dir}" = "$0" ] && dir="${0%\\*}" # a Windows path, e.g. from Python's subprocess
[ "${dir}" = "$0" ] && dir="."
version_file="${dir}/../.python-version"
minimum=""
if [ -r "${version_file}" ]; then
    # `|| [ -n ... ]` keeps a last line that has no trailing newline.
    while IFS= read -r line || [ -n "${line}" ]; do
        line="${line%"${line##*[![:space:]]}"}" # trailing space, CR (CRLF checkout)
        line="${line#"${line%%[![:space:]]*}"}" # leading space
        case "${line}" in
        '' | '#'*) continue ;;
        *) ;;
        esac
        minimum="${line}"
        break
    done <"${version_file}"
fi
# major.minor with an optional numeric patch (3.14 or 3.14.2); only major.minor counts.
case "${minimum}" in
*[!0-9.]* | .* | *. | *..* | *.*.*.*) bad=1 ;;
*) bad="" ;;
esac
case "${minimum}" in
*.*) ;;
*) bad=1 ;;
esac
if [ -n "${bad}" ]; then
    printf '%s\n' "scripts/py.sh: ${version_file} must hold a Python version such as 3.14 or 3.14.2, not '${minimum}'." >&2
    exit 1
fi
min_major="${minimum%%.*}"
min_minor="${minimum#*.}"
min_minor="${min_minor%%.*}"
nl='
'
tried=""

probe='import sys; sys.stdout.write("%d.%d" % sys.version_info[:2])'

for candidate in mise python3 "py -3" python; do
    if [ "${candidate}" = mise ]; then
        # `mise which` finds the installed .python-version Python whether or not
        # mise is activated in this shell; it fails when that one isn't installed.
        if ! command -v mise >/dev/null 2>&1; then
            tried="${tried}${nl}  mise: not on PATH"
            continue
        fi
        if ! path="$(mise -C "${dir}/.." which python 2>/dev/null)" || [ -z "${path}" ]; then
            tried="${tried}${nl}  mise: Python ${min_major}.${min_minor} not installed"
            continue
        fi
        version="$("${path}" -c "${probe}" 2>/dev/null)"
    elif ! path="$(command -v "${candidate%% *}" 2>/dev/null)"; then
        tried="${tried}${nl}  ${candidate}: not on PATH"
        continue
    else
        # shellcheck disable=SC2086 # split "py -3" into the command and its flag
        version="$(${candidate} -c "${probe}" 2>/dev/null)"
    fi
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
        [ "${candidate}" = mise ] && exec "${path}" "$@"
        # shellcheck disable=SC2086 # see above
        exec ${candidate} "$@"
    fi
    tried="${tried}${nl}  ${candidate} (${path}): Python ${version}, too old"
done

# printf is a builtin, so this still prints when PATH has no coreutils.
printf '%s\n' "scripts/py.sh: no Python >= ${min_major}.${min_minor} found. Tried:${tried}" \
    "Run \`mise install\` in the repo to install Python ${min_major}.${min_minor} from .python-version" \
    "(see CONTRIBUTING.md), or install Python ${min_major}.${min_minor}+ from https://www.python.org/downloads/." >&2
exit 1
