#!/bin/bash

# Validate APM primitives in .apm/ and repo-local prompts in .github/prompts/.
#
# .apm/ is the single source of truth. Each primitive must:
#   - start with YAML frontmatter (--- ... ---)
#   - declare a non-empty `description` (APM-preserved, required for discoverability)
#   - declare a `category` (used to group the generated index)
#   - have a non-empty body after the frontmatter (delivered to the harness)

set -euo pipefail
shopt -s globstar nullglob

EXIT_CODE=0

echo "🔍 Validating APM primitives..."
echo ""

# Print the body (everything after the closing frontmatter ---).
body_after_frontmatter() {
    awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$1"
}

for file in .apm/prompts/**/*.prompt.md; do
    [ -f "${file}" ] || continue
    echo "Checking ${file}..."
    FILE_VALID=1

    FRONTMATTER_OK=0
    head -n 1 "${file}" | grep -q "^---$" && FRONTMATTER_OK=1
    if [ "${FRONTMATTER_OK}" -eq 0 ]; then
        echo "❌ Missing YAML frontmatter in ${file}"
        EXIT_CODE=1
        FILE_VALID=0
    else
        if ! grep -q "^description:" "${file}"; then
            echo "❌ Missing 'description' field in frontmatter in ${file}"
            EXIT_CODE=1
            FILE_VALID=0
        fi
        if ! grep -q "^category:" "${file}"; then
            echo "❌ Missing 'category' field in frontmatter in ${file}"
            EXIT_CODE=1
            FILE_VALID=0
        fi
        body=$(body_after_frontmatter "${file}" | tr -d '[:space:]')
        if [ -z "${body}" ]; then
            echo "❌ Empty prompt body in ${file}"
            EXIT_CODE=1
            FILE_VALID=0
        fi
    fi

    [ "${FILE_VALID}" -eq 1 ] && echo "✅ ${file} is valid"
    echo ""
done

# Repo-local Copilot prompts (not part of the shipped package).
for file in .github/prompts/**/*.md; do
    [ -f "${file}" ] || continue
    # Skip APM-deployed copies (their .apm/prompts source is validated above).
    base=$(basename "${file}")
    [ -f ".apm/prompts/${base}" ] && continue
    echo "Checking ${file}..."
    FRONTMATTER_OK=0
    head -n 1 "${file}" | grep -q "^---$" && FRONTMATTER_OK=1
    if [ "${FRONTMATTER_OK}" -eq 1 ] && grep -q "^description:" "${file}"; then
        echo "✅ ${file} is valid"
    else
        echo "❌ File in .github/prompts must use YAML frontmatter with a description in ${file}"
        EXIT_CODE=1
    fi
    echo ""
done

# APM instruction primitives: require description + applyTo + a non-empty body.
for file in .apm/instructions/**/*.instructions.md; do
    [ -f "${file}" ] || continue
    echo "Checking ${file}..."
    FILE_VALID=1

    FRONTMATTER_OK=0
    head -n 1 "${file}" | grep -q "^---$" && FRONTMATTER_OK=1
    if [ "${FRONTMATTER_OK}" -eq 0 ]; then
        echo "❌ Missing YAML frontmatter in ${file}"
        EXIT_CODE=1
        FILE_VALID=0
    else
        if ! grep -q "^description:" "${file}"; then
            echo "❌ Missing 'description' field in frontmatter in ${file}"
            EXIT_CODE=1
            FILE_VALID=0
        fi
        if ! grep -q "^applyTo:" "${file}"; then
            echo "❌ Missing 'applyTo' field in frontmatter in ${file}"
            EXIT_CODE=1
            FILE_VALID=0
        fi
        body=$(body_after_frontmatter "${file}" | tr -d '[:space:]')
        if [ -z "${body}" ]; then
            echo "❌ Empty instruction body in ${file}"
            EXIT_CODE=1
            FILE_VALID=0
        fi
    fi

    [ "${FILE_VALID}" -eq 1 ] && echo "✅ ${file} is valid"
    echo ""
done

# APM skill primitives: require name + description + a non-empty body.
for file in .apm/skills/**/SKILL.md; do
    [ -f "${file}" ] || continue
    echo "Checking ${file}..."
    FILE_VALID=1

    FRONTMATTER_OK=0
    head -n 1 "${file}" | grep -q "^---$" && FRONTMATTER_OK=1
    if [ "${FRONTMATTER_OK}" -eq 0 ]; then
        echo "❌ Missing YAML frontmatter in ${file}"
        EXIT_CODE=1
        FILE_VALID=0
    else
        if ! grep -q "^name:" "${file}"; then
            echo "❌ Missing 'name' field in frontmatter in ${file}"
            EXIT_CODE=1
            FILE_VALID=0
        fi
        if ! grep -q "^description:" "${file}"; then
            echo "❌ Missing 'description' field in frontmatter in ${file}"
            EXIT_CODE=1
            FILE_VALID=0
        fi
        body=$(body_after_frontmatter "${file}" | tr -d '[:space:]')
        if [ -z "${body}" ]; then
            echo "❌ Empty skill body in ${file}"
            EXIT_CODE=1
            FILE_VALID=0
        fi
        # APM requires the frontmatter name to equal the parent directory name.
        skill_parent=$(dirname "${file}")
        skill_dir=$(basename "${skill_parent}")
        skill_name=$(awk -F': *' 'NR>1 && /^name:/ {gsub(/^["'\'']|["'\'']$/,"",$2); print $2; exit}' "${file}")
        if [ -n "${skill_name}" ] && [ "${skill_name}" != "${skill_dir}" ]; then
            echo "❌ Skill 'name' (${skill_name}) must equal its directory name (${skill_dir}) in ${file}"
            EXIT_CODE=1
            FILE_VALID=0
        fi
    fi

    [ "${FILE_VALID}" -eq 1 ] && echo "✅ ${file} is valid"
    echo ""
done

# APM agent primitives: require name + description + a non-empty body.
for file in .apm/agents/**/*.agent.md; do
    [ -f "${file}" ] || continue
    echo "Checking ${file}..."
    FILE_VALID=1

    FRONTMATTER_OK=0
    head -n 1 "${file}" | grep -q "^---$" && FRONTMATTER_OK=1
    if [ "${FRONTMATTER_OK}" -eq 0 ]; then
        echo "❌ Missing YAML frontmatter in ${file}"
        EXIT_CODE=1
        FILE_VALID=0
    else
        if ! grep -q "^name:" "${file}"; then
            echo "❌ Missing 'name' field in frontmatter in ${file}"
            EXIT_CODE=1
            FILE_VALID=0
        fi
        if ! grep -q "^description:" "${file}"; then
            echo "❌ Missing 'description' field in frontmatter in ${file}"
            EXIT_CODE=1
            FILE_VALID=0
        fi
        body=$(body_after_frontmatter "${file}" | tr -d '[:space:]')
        if [ -z "${body}" ]; then
            echo "❌ Empty agent body in ${file}"
            EXIT_CODE=1
            FILE_VALID=0
        fi
    fi

    [ "${FILE_VALID}" -eq 1 ] && echo "✅ ${file} is valid"
    echo ""
done

if [ "${EXIT_CODE}" -eq 0 ]; then
    echo "✅ All primitives are properly structured!"
else
    echo "❌ Some primitives are missing required fields"
fi

exit "${EXIT_CODE}"
