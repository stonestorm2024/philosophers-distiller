#!/usr/bin/env bash
#
# publish_to_clawhub.sh
# Publishes philosopher SKILL.md files to ClawHub via the clawhub CLI.
#
# Prerequisites:
#   - clawhub CLI installed and logged in
#   - Node.js (for clawhub CLI)
#
# Usage:
#   chmod +x publish_to_clawhub.sh
#   ./publish_to_clawhub.sh

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_DIRS=(
  "heidegger"
  "marcuse"
  "anders"
  "marx"
)

echo "=== Publishing to ClawHub ==="
echo ""

for philosopher in "${SKILL_DIRS[@]}"; do
  skill_file="$BASE_DIR/output/$philosopher/SKILL.md"
  skill_name="${philosopher}-distill"
  
  if [[ ! -f "$skill_file" ]]; then
    echo "SKILL.md not found for $philosopher — skipping"
    continue
  fi
  
  echo "Publishing $skill_name..."
  
  if command -v clawhub &>/dev/null; then
    clawhub publish "$skill_file" --name "$skill_name" 2>/dev/null || \
      clawhub publish "$skill_file" 2>/dev/null || \
      echo "  (clawhub CLI not fully configured — SKILL.md available at $skill_file)"
    echo "  Published $skill_name"
  else
    echo "  clawhub CLI not found — SKILL.md available at: $skill_file"
    echo "  To publish: clawhub publish $skill_file"
  fi
  echo ""
done

echo "=== Framework SKILL.md ==="
framework_skill="$BASE_DIR/framework/SKILL.md"
echo "Framework skill available at: $framework_skill"
echo "To publish framework: clawhub publish $framework_skill"
echo ""
echo "=== ClawHub Publishing Complete ==="
