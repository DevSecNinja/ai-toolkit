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

cat > INDEX.md << 'EOF'
# 📑 Primitive Index

> Auto-generated index of all available APM primitives

EOF

echo "## 📂 Prompts" >> INDEX.md
echo "" >> INDEX.md

# Collect categories from frontmatter, unique + sorted.
categories=$(for f in .apm/prompts/*.prompt.md; do get_field "$f" category; done | sort -u)

while IFS= read -r category; do
  [ -n "$category" ] || continue
  echo "### 📁 $(titlecase "$category")" >> INDEX.md
  echo "" >> INDEX.md
  for f in .apm/prompts/*.prompt.md; do
    [ "$(get_field "$f" category)" = "$category" ] || continue
    title=$(get_field "$f" title)
    description=$(get_field "$f" description)
    echo "- **[${title}](/${f})** - ${description}" >> INDEX.md
  done
  echo "" >> INDEX.md
done <<< "$categories"

# Process APM instruction primitives (shipped in the package).
if compgen -G ".apm/instructions/*.instructions.md" > /dev/null; then
  echo "## 📐 Instructions" >> INDEX.md
  echo "" >> INDEX.md
  echo "> Long-lived behavior rules deployed to each harness's instruction directory" >> INDEX.md
  echo "" >> INDEX.md
  for f in .apm/instructions/*.instructions.md; do
    title=$(basename "$f" .instructions.md); title=$(titlecase "$title")
    description=$(get_field "$f" description)
    applyTo=$(get_field "$f" applyTo)
    echo "- **[${title}](/${f})** (\`${applyTo}\`) - ${description}" >> INDEX.md
  done
  echo "" >> INDEX.md
fi

# Process APM skill primitives (shipped in the package).
if compgen -G ".apm/skills/*/SKILL.md" > /dev/null; then
  echo "## 🧠 Skills" >> INDEX.md
  echo "" >> INDEX.md
  echo "> Model-invoked guides deployed to each harness's skills directory" >> INDEX.md
  echo "" >> INDEX.md
  for f in .apm/skills/*/SKILL.md; do
    name=$(basename "$(dirname "$f")"); title=$(titlecase "$name")
    description=$(get_field "$f" description)
    echo "- **[${title}](/${f})** - ${description}" >> INDEX.md
  done
  echo "" >> INDEX.md
fi

# Process APM agent primitives (shipped in the package).
if compgen -G ".apm/agents/*.agent.md" > /dev/null; then
  echo "## 🧑‍✈️ Agents" >> INDEX.md
  echo "" >> INDEX.md
  echo "> Invocable specialist personas deployed to each harness's agents directory" >> INDEX.md
  echo "" >> INDEX.md
  for f in .apm/agents/*.agent.md; do
    title=$(get_field "$f" name); [ -n "$title" ] || title=$(titlecase "$(basename "$f" .agent.md)")
    description=$(get_field "$f" description)
    echo "- **[${title}](/${f})** - ${description}" >> INDEX.md
  done
  echo "" >> INDEX.md
fi

# Bundled agents materialized from APM dependencies. These are committed under
# .github/agents/ as a reviewable snapshot (the prompt-hijacking review gate);
# skip our own agents' deploy copies (those are authored under .apm/agents/).
if compgen -G ".github/agents/*.agent.md" > /dev/null; then
  printed_header=0
  for f in .github/agents/*.agent.md; do
    [ -f ".apm/agents/$(basename "$f")" ] && continue
    if [ "$printed_header" -eq 0 ]; then
      echo "## 🤝 Bundled Agents" >> INDEX.md
      echo "" >> INDEX.md
      echo "> External agents pulled via APM dependencies, committed here as a reviewable snapshot (see \`apm.yml\`)" >> INDEX.md
      echo "" >> INDEX.md
      printed_header=1
    fi
    title=$(get_field "$f" name); [ -n "$title" ] || title=$(titlecase "$(basename "$f" .agent.md)")
    description=$(get_field "$f" description)
    echo "- **[${title}](/${f})** - ${description}" >> INDEX.md
  done
  [ "$printed_header" -eq 1 ] && echo "" >> INDEX.md
fi

# Process .github/prompts directory (repo-local Copilot prompts, not part of the package).
if [ -d ".github/prompts" ]; then
  echo "## 🤖 GitHub Copilot Prompts" >> INDEX.md
  echo "" >> INDEX.md
  echo "> Prompts optimized for use with GitHub Copilot in this repository" >> INDEX.md
  echo "" >> INDEX.md
  for f in .github/prompts/*.md; do
    base=$(basename "$f")
    # Skip APM-deployed copies (their .apm/prompts source is already indexed above).
    [ -f ".apm/prompts/$base" ] && continue
    title=$(basename "$f" .md); title=$(basename "$title" .prompt); title=$(titlecase "$title")
    description=$(get_field "$f" description)
    echo "- **[${title}](/${f})** - ${description}" >> INDEX.md
  done
fi

cat >> INDEX.md << 'EOF'

---

*This index is automatically generated from the `.apm/` primitives.*
EOF

echo "✅ Index generated successfully!"

echo "📝 Injecting index into README.md..."
INDEX_CONTENT=$(tail -n +4 INDEX.md | head -n -3)
awk -v index_content="$INDEX_CONTENT" '
  BEGIN { in_section=0 }
  /<!-- INDEX_START -->/ {
    print
    print "<!-- This section is auto-generated by scripts/generate-index.sh -->"
    print ""
    print index_content
    in_section=1
    next
  }
  /<!-- INDEX_END -->/ { in_section=0 }
  !in_section { print }
' README.md > README.md.tmp && mv README.md.tmp README.md

echo "✅ README.md updated with latest index!"
