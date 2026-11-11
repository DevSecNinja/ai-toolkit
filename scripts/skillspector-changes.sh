#!/usr/bin/env bash
# Decide whether this event needs a SkillSpector scan; writes relevant=true|false.
# Pull requests are checked out at their merge commit, so HEAD^1..HEAD is the PR diff.
set -euo pipefail

pattern='^(apm\.yml|apm\.lock\.yaml|\.apm/|\.agents/|\.github/(agents|prompts|instructions|hooks)/'
pattern+='|\.github/skillspector-accepted\.json|\.github/workflows/skillspector\.yml'
pattern+='|scripts/(scan-skills\.py|skillspector-report\.py|skillspector-changes\.sh|git-push-approval/|tool-guardian/)'
pattern+='|tests/(test_skillspector|test_skillspector_report|smoke-skillspector)\.py$)'

relevant=true
# Anything other than a pull request merge commit scans everything (fail closed).
if [[ ${GITHUB_EVENT_NAME:-} == "pull_request" ]] && git rev-parse --verify --quiet HEAD^2 >/dev/null; then
    changed=$(git diff --name-only HEAD^1 HEAD)
    if ! grep -Eq "${pattern}" <<<"${changed}"; then
        relevant=false
    fi
fi
echo "relevant=${relevant}" | tee -a "${GITHUB_OUTPUT:-/dev/null}"
