#!/bin/bash

# Git Push Approval Hook
# Forces an explicit, interactive human approval before the AI coding agent runs
# any `git push`. A commit is entirely local and rewritable (amend / reset /
# rebase) until it is pushed, so `git push` is the first irreversible step that
# publishes work to a remote — the right place for a human checkpoint.
#
# Runs as a Copilot `preToolUse` command hook. It reads the tool invocation as
# JSON on stdin and, when the tool is a shell command that contains a `git push`,
# emits a `permissionDecision: "ask"` object so the CLI prompts the user to
# approve. For every other tool call it emits no decision and lets the normal
# permission flow proceed.
#
# Feature-branch pushes are the exception (#228): when every `git push` in the
# command provably targets a non-default, non-protected branch on `origin`
# (including `--force-with-lease`), the hook stays silent so unattended
# autopilot sessions can update their own PR branches. Anything it can't resolve
# with certainty still asks. See docs/git-push-approval.md.
#
# IMPORTANT: `preToolUse` command hooks are fail-closed — a non-zero exit (or a
# crash) denies the tool call. This script therefore always exits 0 and only
# ever upgrades the decision to "ask"; it never blocks unrelated tools.
#
# Environment variables:
#   SKIP_PUSH_APPROVAL - "true" to disable the guardrail entirely (default: unset)
#
# See docs: https://docs.github.com/en/copilot/reference/hooks-reference

set -uo pipefail

# Escape hatch: allow operators to turn the guardrail off for a session.
if [[ "${SKIP_PUSH_APPROVAL:-}" == "true" ]]; then
    exit 0
fi

# Read the tool invocation payload from stdin.
INPUT="$(cat)"

# Extract the tool name and its arguments, tolerating both the camelCase payload
# (toolName / toolArgs) and the VS Code compatible payload (tool_name / tool_input).
TOOL_NAME=""
TOOL_ARGS=""
# The exact command text, only when jq could extract it; the feature-branch
# check never parses the raw payload.
COMMAND=""
HOOK_CWD=""

if command -v jq &>/dev/null; then
    TOOL_NAME="$(printf '%s' "${INPUT}" | jq -r '.toolName // .tool_name // empty' 2>/dev/null || printf '')"
    TOOL_ARGS="$(printf '%s' "${INPUT}" | jq -r '
        (.toolArgs // .tool_input // empty) as $a
        | if ($a | type) == "string" then $a
          elif ($a | type) == "object" then ($a.command // $a.cmd // $a.script // ($a | tojson))
          else ($a | tojson) end' 2>/dev/null || printf '')"
    # Copilot CLI sends toolArgs as a JSON-encoded string; VS Code sends an object.
    COMMAND="$(printf '%s' "${INPUT}" | jq -r '
        (.toolArgs // .tool_input // empty) as $a
        | (if ($a | type) == "string" then ($a | try fromjson catch $a) else $a end) as $p
        | if ($p | type) == "object" then ($p.command // $p.cmd // $p.script // empty)
          elif ($p | type) == "string" then $p
          else empty end' 2>/dev/null || printf '')"
    HOOK_CWD="$(printf '%s' "${INPUT}" | jq -r '.cwd // empty' 2>/dev/null || printf '')"
fi
[[ -n "${HOOK_CWD}" && -d "${HOOK_CWD}" ]] || HOOK_CWD="${PWD}"

# Fallback when jq is unavailable or produced nothing: scan the raw payload.
if [[ -z "${TOOL_NAME}" ]]; then
    TOOL_NAME="$(printf '%s' "${INPUT}" |
        grep -oiE '"tool_?[nN]ame"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 |
        sed -E 's/.*:[[:space:]]*"//; s/"$//' || printf '')"
fi
if [[ -z "${TOOL_ARGS}" ]]; then
    TOOL_ARGS="${INPUT}"
fi

# Only shell-execution tools can run `git push`. Gate on the tool name so that,
# for example, editing a document that merely mentions "git push" is unaffected.
# An empty/unknown tool name falls through to scanning, erring toward asking.
# Lowercase with `tr`, not `${1,,}`: stock macOS runs this under Bash 3.2.
is_shell_tool() {
    local name
    name="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
    case "${name}" in
    bash | powershell | shell | "") return 0 ;;
    *) return 1 ;;
    esac
}

# Match `git ... push` within a single command: `git push`, `git push origin main`,
# `git -C /repo push`, `/usr/bin/git --no-pager push`. Intervening tokens may be
# flags or values but must not cross a command separator (; & |), so unrelated
# commands like `git status && npm run push` do not trigger a prompt. The trailing
# boundary accepts any non-word character (or end of string) so the match still
# holds when scanning JSON-embedded command text (e.g. `git push"`).
GIT_PUSH_REGEX='(^|[^[:alnum:]_])git([[:space:]]+[^[:space:];&|]+)*[[:space:]]+push([^[:alnum:]_]|$)'

# --- Feature-branch pushes (#228) ---------------------------------------------
# Every helper below returns non-zero when it can't prove a push is safe, and the
# caller then asks. Bash 3.2 compatible: no ${var,,}, no empty "${arr[@]}".

SEP=$'\x1e' # marks a command boundary in WORDS
REPO_DIR=""
DEFAULT_BRANCH=""
HEAD_MAY_MOVE=0
CREATED=""
CURRENT=""
WORDS=()
SEG=()
POS=()

rgit() { git -C "${REPO_DIR}" "$@" 2>/dev/null; }

is_protected() {
    case "$1" in
    "" | HEAD | main | master | trunk | develop | gh-pages | release | release/* | releases/* | release-please--*) return 0 ;;
    *) ;;
    esac
    [[ -n "${DEFAULT_BRANCH}" && "$1" == "${DEFAULT_BRANCH}" ]]
}

flush_word() {
    if [[ ${inword} -eq 1 ]]; then
        if [[ ${skip} -eq 1 ]]; then skip=0; else WORDS+=("${word}"); fi
    fi
    word=""
    inword=0
}

# Split a command into words (quotes removed), with SEP between commands and
# redirections dropped. Fails on anything whose expansion can't be predicted.
tokenize() {
    local s="$1" n=${#1} i=0 c next q="" word="" inword=0 skip=0
    WORDS=()
    case "${s}" in *'$'* | *'`'* | *\\* | *"${SEP}"*) return 1 ;; *) ;; esac
    while [[ ${i} -lt ${n} ]]; do
        c="${s:${i}:1}"
        i=$((i + 1))
        if [[ -n "${q}" ]]; then
            if [[ "${c}" == "${q}" ]]; then q=""; else word="${word}${c}"; fi
            continue
        fi
        case "${c}" in
        "'" | '"') q="${c}" && inword=1 ;;
        ' ' | $'\t' | $'\r') flush_word ;;
        $'\n' | ';' | '|' | '&' | '(' | ')') flush_word && WORDS+=("${SEP}") ;;
        '>' | '<')
            next="${s:${i}:1}"
            [[ "${next}" == '(' || "${c}${next}" == '<<' ]] && return 1
            case "${next}" in '>' | '&' | '|') i=$((i + 1)) ;; *) ;; esac
            case "${word}" in *[!0-9]*) ;; *) word="" && inword=0 ;; esac # fd, as in 2>&1
            flush_word
            skip=1
            ;;
        '#' | '~')
            [[ ${inword} -eq 1 ]] || return 1 # a comment or tilde expansion
            word="${word}${c}"
            ;;
        '*' | '?' | '[' | ']' | '{' | '}') return 1 ;; # unquoted glob or brace expansion
        *) word="${word}${c}" && inword=1 ;;
        esac
    done
    [[ -z "${q}" ]] || return 1
    flush_word
    [[ ${skip} -eq 0 ]]
}

# Run scan_command ("$1" = scan) or check_command on each command in WORDS,
# with SEG set to its words.
for_each_command() {
    local i=0 n=${#WORDS[@]}
    SEG=()
    while [[ ${i} -le ${n} ]]; do
        if [[ ${i} -eq ${n} || "${WORDS[${i}]}" == "${SEP}" ]]; then
            if [[ ${#SEG[@]} -gt 0 ]]; then
                if [[ "$1" == scan ]]; then scan_command || return 1; else check_command || return 1; fi
            fi
            SEG=()
        else
            SEG+=("${WORDS[${i}]}")
        fi
        i=$((i + 1))
    done
}

# Set SUB / SUB_AT when SEG is a plain `git [--no-pager] <subcommand> ...`.
# Other global options (-c, -C, --git-dir, ...) can change the repository,
# config or aliases, so they don't count as plain.
git_subcommand() {
    local i=1
    SUB=""
    SUB_AT=0
    case "${SEG[0]}" in git | */git | git.exe | */git.exe) ;; *) return 1 ;; esac
    while [[ ${i} -lt ${#SEG[@]} && ("${SEG[${i}]}" == "--no-pager" || "${SEG[${i}]}" == "-P") ]]; do
        i=$((i + 1))
    done
    [[ ${i} -lt ${#SEG[@]} ]] || return 1
    SUB="${SEG[${i}]}"
    SUB_AT=$((i + 1))
}

# First pass: every command must be on a short allowlist that can't change the
# directory, push config or remotes, nor run other programs. Note commands that
# move HEAD or create branches.
scan_command() {
    local i positional=0
    case "${SEG[0]}" in
    echo | head | tail | grep | wc | true)
        ! grep -qiE "${GIT_PUSH_REGEX}" <<<"${SEG[*]}"
        return
        ;;
    *) ;;
    esac
    git_subcommand || return 1
    i=${SUB_AT}
    while [[ ${i} -lt ${#SEG[@]} ]]; do
        case "${SEG[${i}]}" in -x | --exec* | --upload-pack* | --receive-pack*) return 1 ;; *) ;; esac
        i=$((i + 1))
    done
    i=${SUB_AT}
    # Built-in names only: git aliases can't shadow them.
    case "${SUB}" in
    push) return 0 ;;
    add | commit | diff | fetch | log | rev-parse | show | status) ;;
    checkout | switch)
        HEAD_MAY_MOVE=1
        while [[ ${i} -lt $((${#SEG[@]} - 1)) ]]; do
            case "${SEG[${i}]}" in -b | -B | -c | -C) CREATED="${CREATED}${SEP}${SEG[$((i + 1))]}${SEP}" ;; *) ;; esac
            i=$((i + 1))
        done
        ;;
    branch) HEAD_MAY_MOVE=1 ;;
    rebase)
        # `git rebase <upstream> <branch>` checks out <branch> first.
        while [[ ${i} -lt ${#SEG[@]} ]]; do
            case "${SEG[${i}]}" in -*) ;; *) positional=$((positional + 1)) ;; esac
            i=$((i + 1))
        done
        [[ ${positional} -le 1 ]] || HEAD_MAY_MOVE=1
        ;;
    *) return 1 ;;
    esac
    ! grep -qiE "${GIT_PUSH_REGEX}" <<<"${SEG[*]}"
}

current_branch() {
    [[ ${HEAD_MAY_MOVE} -eq 0 ]] || return 1
    CURRENT="$(rgit symbolic-ref --quiet --short HEAD)" && [[ -n "${CURRENT}" ]]
}

# `git push [origin]`: targets follow from the current branch, its upstream and
# push config; only the default-like push.default modes are resolved.
push_current() {
    local remote="$1" merge mode
    current_branch || return 1
    mode="$(rgit config --get push.default)"
    case "${mode}" in "" | simple | current | upstream) ;; *) return 1 ;; esac
    if [[ -z "${remote}" ]]; then
        remote="$(rgit config --get "branch.${CURRENT}.pushRemote" ||
            rgit config --get remote.pushDefault ||
            rgit config --get "branch.${CURRENT}.remote" || printf origin)"
    fi
    [[ "${remote}" == "origin" ]] || return 1
    merge="$(rgit config --get "branch.${CURRENT}.merge")"
    if [[ -n "${merge}" ]]; then
        [[ "${merge}" == refs/heads/* ]] || return 1
        is_protected "${merge#refs/heads/}" && return 1
    fi
    ! is_protected "${CURRENT}"
}

check_refspec() {
    local src="$1" dst
    if [[ "$1" == *:* ]]; then
        # Git resolves an unqualified destination against the remote's refs,
        # which may hold a tag of that name, so require refs/heads/.
        dst="${1#*:}"
        [[ -n "${1%%:*}" && "${dst}" == refs/heads/* && "${dst}" != *:* ]] || return 1
        ! is_protected "${dst#refs/heads/}"
        return
    fi
    # A source-only refspec pushes to the same ref name, so it must be a branch
    # (existing, or created earlier in the command).
    if [[ "${src}" == HEAD ]]; then
        current_branch || return 1
        src="${CURRENT}"
    fi
    src="${src#refs/heads/}"
    rgit show-ref --verify --quiet "refs/tags/${src}" && return 1
    rgit show-ref --verify --quiet "refs/heads/${src}" ||
        [[ "${CREATED}" == *"${SEP}${src}${SEP}"* ]] || return 1
    ! is_protected "${src}"
}

check_push() {
    local i=${SUB_AT} a options=1
    POS=()
    while [[ ${i} -lt ${#SEG[@]} ]]; do
        a="${SEG[${i}]}"
        i=$((i + 1))
        if [[ ${options} -eq 1 ]]; then
            case "${a}" in
            --) options=0 && continue ;;
            -u | --set-upstream | -q | --quiet | -v | --verbose | -n | --dry-run | --progress | --no-progress | \
                --porcelain | --atomic | --force-with-lease | --force-with-lease=* | --force-if-includes) continue ;;
            -*) return 1 ;; # --force, --tags, --all, --mirror, --delete, --no-verify, ...
            *) ;;
            esac
        fi
        case "${a}" in "" | +* | *[*?{}~,@^]* | *'['* | *']'*) return 1 ;; *) ;; esac
        POS+=("${a}")
    done
    [[ ${#POS[@]} -gt 0 ]] || {
        push_current ""
        return
    }
    [[ "${POS[0]}" == "origin" ]] || return 1
    [[ ${#POS[@]} -gt 1 ]] || {
        push_current origin
        return
    }
    i=1
    while [[ ${i} -lt ${#POS[@]} ]]; do
        check_refspec "${POS[${i}]}" || return 1
        i=$((i + 1))
    done
}

# Second pass: every push must target a feature branch.
check_command() {
    if git_subcommand && [[ "${SUB}" == "push" ]]; then
        check_push
        return
    fi
    return 0
}

# push_is_safe DIR COMMAND
push_is_safe() {
    local mirror follow refspecs
    REPO_DIR="$1"
    rgit rev-parse --git-dir >/dev/null || return 1
    # Config that silently adds or remaps targets: mirroring, tag following and
    # remote.origin.push refspecs (which also remap source-only refspecs).
    mirror="$(rgit config --get --bool remote.origin.mirror)"
    follow="$(rgit config --get --bool push.followTags)"
    refspecs="$(rgit config --get-all remote.origin.push)"
    [[ "${mirror}" != true && "${follow}" != true && -z "${refspecs}" ]] || return 1
    # An unknown default branch can't be told apart from a feature branch.
    DEFAULT_BRANCH="$(rgit symbolic-ref --quiet --short refs/remotes/origin/HEAD)"
    DEFAULT_BRANCH="${DEFAULT_BRANCH#origin/}"
    [[ -n "${DEFAULT_BRANCH}" ]] || return 1
    tokenize "$2" || return 1
    for_each_command scan && for_each_command check
}

if is_shell_tool "${TOOL_NAME}" && printf '%s' "${TOOL_ARGS}" | grep -qiE "${GIT_PUSH_REGEX}"; then
    if [[ -n "${COMMAND}" ]] && push_is_safe "${HOOK_CWD}" "${COMMAND}"; then
        exit 0
    fi
    REASON="git push publishes commits to a remote and is irreversible. Pushes to a feature branch on origin are allowed without a prompt, but this one targets the default or a protected branch, a tag or another remote, forces without a lease, or could not be verified, so it needs explicit human approval. Set SKIP_PUSH_APPROVAL=true to disable the guardrail."
    # Emit exactly one decision object. jq keeps the reason safely JSON-escaped;
    # the printf fallback covers environments without jq.
    if command -v jq &>/dev/null; then
        jq -cn --arg reason "${REASON}" '{permissionDecision: "ask", permissionDecisionReason: $reason}'
    else
        printf '{"permissionDecision":"ask","permissionDecisionReason":"%s"}\n' \
            "git push is irreversible and requires explicit human approval. Set SKIP_PUSH_APPROVAL=true to disable."
    fi
fi

# Always succeed: fail-closed hooks would otherwise deny unrelated tool calls.
exit 0
