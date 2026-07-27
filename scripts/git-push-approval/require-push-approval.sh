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

if command -v jq &>/dev/null; then
    TOOL_NAME="$(printf '%s' "${INPUT}" | jq -r '.toolName // .tool_name // empty' 2>/dev/null || printf '')"
    TOOL_ARGS="$(printf '%s' "${INPUT}" | jq -r '
        (.toolArgs // .tool_input // empty) as $a
        | if ($a | type) == "string" then $a
          elif ($a | type) == "object" then ($a.command // $a.cmd // $a.script // ($a | tojson))
          else ($a | tojson) end' 2>/dev/null || printf '')"
fi

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
is_shell_tool() {
    case "${1,,}" in
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

if is_shell_tool "${TOOL_NAME}" && printf '%s' "${TOOL_ARGS}" | grep -qiE "${GIT_PUSH_REGEX}"; then
    REASON="git push publishes commits to a remote and is irreversible, unlike local commits (which can still be amended, reset, or rebased). This repository's guardrail requires explicit human approval for every push. Set SKIP_PUSH_APPROVAL=true to disable it."
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
