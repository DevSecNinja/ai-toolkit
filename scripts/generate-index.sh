#!/bin/bash

# Script to generate INDEX.md from the APM primitives in .apm/.
#
# .apm/ is the single source of truth. Prompt primitives
# (.apm/prompts/<category>-<name>.prompt.md) carry `title`, `category` and
# `description`; instruction primitives (.apm/instructions/<name>.instructions.md)
# carry `description` and `applyTo`. This script reads those and writes INDEX.md
# plus the auto-generated block in README.md.

set -euo pipefail
shopt -s nullglob

echo "📑 Generating prompt index..."

# Extract a single scalar frontmatter field (handles quoted values).
get_field() {
    awk -v key="$2" '
    NR==1 && $0!="---" { exit }
    NR==1 { infm=1; next }
    infm && $0=="---" { exit }
    infm {
      if ($0 ~ "^" key ":") {
        sub("^" key ": *", "")
        gsub(/^["'\'']|["'\'']$/, "")
        print
        exit
      }
    }
  ' "$1"
}

# Title-case a slug like "home-assistant" -> "Home Assistant".
titlecase() {
    echo "$1" | sed 's/-/ /g' | awk '{ for (i=1;i<=NF;i++){ $i=toupper(substr($i,1,1)) substr($i,2) } print }'
}

# Everything below is written to INDEX.md through a single redirect so the
# generated file is assembled in one place (and shellcheck stays happy).
{
    cat <<'EOF'
# 📑 Primitive Index

> Auto-generated index of all available APM primitives

EOF

    echo "## 📂 Prompts"
    echo ""

    # Collect categories from frontmatter, unique + sorted.
    categories=$(for f in .apm/prompts/*.prompt.md; do get_field "${f}" category; done | sort -u)

    while IFS= read -r category; do
        [ -n "${category}" ] || continue
        category_title=$(titlecase "${category}")
        echo "### 📁 ${category_title}"
        echo ""
        for f in .apm/prompts/*.prompt.md; do
            file_category=$(get_field "${f}" category)
            [ "${file_category}" = "${category}" ] || continue
            title=$(get_field "${f}" title)
            description=$(get_field "${f}" description)
            echo "- **[${title}](/${f})** - ${description}"
        done
        echo ""
    done <<<"${categories}"

    # Process APM instruction primitives (shipped in the package).
    if compgen -G ".apm/instructions/*.instructions.md" >/dev/null; then
        echo "## 📐 Instructions"
        echo ""
        echo "> Long-lived behavior rules deployed to each harness's instruction directory"
        echo ""
        for f in .apm/instructions/*.instructions.md; do
            title=$(basename "${f}" .instructions.md)
            title=$(titlecase "${title}")
            description=$(get_field "${f}" description)
            applyTo=$(get_field "${f}" applyTo)
            echo "- **[${title}](/${f})** (\`${applyTo}\`) - ${description}"
        done
        echo ""
    fi

    # Process APM skill primitives (shipped in the package).
    if compgen -G ".apm/skills/*/SKILL.md" >/dev/null; then
        echo "## 🧠 Skills"
        echo ""
        echo "> Model-invoked guides deployed to each harness's skills directory"
        echo ""
        for f in .apm/skills/*/SKILL.md; do
            skill_dir=$(dirname "${f}")
            name=$(basename "${skill_dir}")
            title=$(titlecase "${name}")
            description=$(get_field "${f}" description)
            echo "- **[${title}](/${f})** - ${description}"
        done
        echo ""
    fi

    # Process APM agent primitives (shipped in the package).
    if compgen -G ".apm/agents/*.agent.md" >/dev/null; then
        echo "## 🧑‍✈️ Agents"
        echo ""
        echo "> Invocable specialist personas deployed to each harness's agents directory"
        echo ""
        for f in .apm/agents/*.agent.md; do
            title=$(get_field "${f}" name)
            if [ -z "${title}" ]; then
                base=$(basename "${f}" .agent.md)
                title=$(titlecase "${base}")
            fi
            description=$(get_field "${f}" description)
            echo "- **[${title}](/${f})** - ${description}"
        done
        echo ""
    fi

    # Bundled agents materialized from APM dependencies. These are committed under
    # .github/agents/ as a reviewable snapshot (the prompt-hijacking review gate);
    # skip our own agents' deploy copies (those are authored under .apm/agents/).
    if compgen -G ".github/agents/*.agent.md" >/dev/null; then
        printed_header=0
        for f in .github/agents/*.agent.md; do
            base=$(basename "${f}")
            [ -f ".apm/agents/${base}" ] && continue
            if [ "${printed_header}" -eq 0 ]; then
                echo "## 🤝 Bundled Agents"
                echo ""
                echo "> External agents pulled via APM dependencies, committed here as a reviewable snapshot (see \`apm.yml\`)"
                echo ""
                printed_header=1
            fi
            title=$(get_field "${f}" name)
            if [ -z "${title}" ]; then
                title=$(titlecase "${base%.agent.md}")
            fi
            description=$(get_field "${f}" description)
            echo "- **[${title}](/${f})** - ${description}"
        done
        [ "${printed_header}" -eq 1 ] && echo ""
    fi

    # Process .github/prompts directory (repo-local Copilot prompts, not part of the package).
    if [ -d ".github/prompts" ]; then
        echo "## 🤖 GitHub Copilot Prompts"
        echo ""
        echo "> Prompts optimized for use with GitHub Copilot in this repository"
        echo ""
        for f in .github/prompts/*.md; do
            base=$(basename "${f}")
            # Skip APM-deployed copies (their .apm/prompts source is already indexed above).
            [ -f ".apm/prompts/${base}" ] && continue
            title=$(basename "${f}" .md)
            title=$(basename "${title}" .prompt)
            title=$(titlecase "${title}")
            description=$(get_field "${f}" description)
            echo "- **[${title}](/${f})** - ${description}"
        done
    fi

    cat <<'EOF'

---

_This index is automatically generated from the `.apm/` primitives._
EOF
} >INDEX.md

echo "✅ Index generated successfully!"

echo "📝 Injecting index into README.md..."
INDEX_CONTENT=$(tail -n +5 INDEX.md | head -n -3)
awk -v index_content="${INDEX_CONTENT}" '
  BEGIN { in_section=0 }
  /<!-- INDEX_START -->/ {
    print
    print "<!-- This section is auto-generated by scripts/generate-index.sh -->"
    print ""
    print index_content
    print ""
    in_section=1
    next
  }
  /<!-- INDEX_END -->/ { in_section=0 }
  !in_section { print }
' README.md >README.md.tmp && mv README.md.tmp README.md

echo "✅ README.md updated with latest index!"
