#!/bin/bash

# Script to reorganize skills into folders with SKILL.md structure

SKILLS_DIR=".claude/skills"

echo "🔧 Reorganizing skills into folder structure..."
echo ""

# Counter for tracking
processed=0
skipped=0

# Loop through all .md files in skills directory
for skill_file in "$SKILLS_DIR"/*.md; do
  # Skip if no .md files found
  if [ ! -f "$skill_file" ]; then
    continue
  fi

  # Extract filename without path and extension
  filename=$(basename "$skill_file")
  skill_name="${filename%.md}"

  # Create folder name (same as skill name)
  folder_name="$SKILLS_DIR/$skill_name"

  echo "📁 Processing: $skill_name"

  # Create folder if it doesn't exist
  mkdir -p "$folder_name"

  # Read the file content
  content=$(cat "$skill_file")

  # Check if file already has YAML frontmatter with name
  if echo "$content" | head -n 10 | grep -q "^name:"; then
    # Just move and rename
    mv "$skill_file" "$folder_name/SKILL.md"
    echo "   ✓ Moved to $folder_name/SKILL.md (frontmatter already has name)"
  else
    # Need to update frontmatter
    # Extract existing frontmatter if present
    if echo "$content" | head -n 1 | grep -q "^---"; then
      # Has frontmatter, extract description
      description=$(echo "$content" | sed -n '/^---$/,/^---$/p' | grep "^description:" | sed 's/^description: //')

      # Extract content after frontmatter
      body=$(echo "$content" | sed '1,/^---$/d' | sed '1,/^---$/d')

      # Create new frontmatter with name and description
      new_content="---
name: $skill_name
description: $description
---
$body"
    else
      # No frontmatter, create new one
      new_content="---
name: $skill_name
description: Skill for $skill_name operations
---

$content"
    fi

    # Write to SKILL.md
    echo "$new_content" > "$folder_name/SKILL.md"

    # Remove old file
    rm "$skill_file"

    echo "   ✓ Created $folder_name/SKILL.md with updated frontmatter"
  fi

  ((processed++))
  echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Reorganization complete!"
echo "   Processed: $processed skills"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
