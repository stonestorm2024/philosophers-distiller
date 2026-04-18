#!/usr/bin/env bash
#
# publish_to_github.sh
# Creates GitHub repos for each philosopher and pushes all persona files.
#
# Prerequisites:
#   - GitHub Fine-Grained PAT stored in GITHUB_TOKEN env var
#   - jq for JSON parsing
#   - curl for API calls
#
# Usage:
#   chmod +x publish_to_github.sh
#   export GITHUB_TOKEN="github_pat_..."
#   ./publish_to_github.sh

set -euo pipefail

# Configuration
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
GITHUB_USER="${GITHUB_USER:-$(curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user | jq -r '.login')}"
REPO_OWNER="${REPO_OWNER:-$GITHUB_USER}"
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRAMEWORK_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Repos to create
REPOS=(
  "heidegger-distill"
  "marcuse-distill"
  "anders-distill"
  "marx-distill"
  "philosophers-distiller"
)

# Initialize Git config (required for git operations)
git config --global user.email "philosophers@distiller.local" 2>/dev/null || true
git config --global user.name "Philosophers Distiller" 2>/dev/null || true

echo "=== GitHub User: $GITHUB_USER ==="
echo ""

# Function: Create repo via GitHub API
create_repo() {
  local repo_name="$1"
  local description="$2"
  
  echo "Creating repository: $repo_name"
  
  # Check if repo already exists
  if curl -s -H "Authorization: token $GITHUB_TOKEN" \
    "https://api.github.com/repos/$REPO_OWNER/$repo_name" | jq -e '.id' > /dev/null 2>&1; then
    echo "  Repository $repo_name already exists — skipping creation"
    return 0
  fi
  
  # Create the repo
  local response
  response=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$repo_name\",\"description\":\"$description\",\"private\":false,\"has_issues\":true,\"has_projects\":false,\"has_wiki\":false,\"auto_init\":true}" \
    "https://api.github.com/user/repos")
  
  local http_code="${response##*$'\n'}"
  local body="${response%$'\n'*}"
  
  if [[ "$http_code" == "201" ]]; then
    echo "  Created $repo_name successfully"
  else
    echo "  Failed to create $repo_name (HTTP $http_code): $body"
  fi
}

# Function: Push files to repo
push_to_repo() {
  local repo_name="$1"
  local source_dir="$2"
  
  echo "Pushing files to $repo_name from $source_dir"
  
  local temp_dir
  temp_dir=$(mktemp -d)
  trap "rm -rf $temp_dir" EXIT
  
  # Clone the repo (or use the initialized one)
  git clone "https://$GITHUB_TOKEN@github.com/$REPO_OWNER/$repo_name.git" "$temp_dir" 2>/dev/null
  
  # Copy files
  if [[ -d "$source_dir" ]]; then
    cp -r "$source_dir"/* "$temp_dir/" 2>/dev/null || true
  fi
  
  # Remove .git from copied files if present
  rm -rf "$temp_dir/.git" 2>/dev/null || true
  
  cd "$temp_dir"
  
  # Add all files
  git add -A 2>/dev/null || true
  
  # Commit
  if git diff --cached --quiet; then
    echo "  No changes to commit for $repo_name"
  else
    git commit -m "Add philosopher persona files" --allow-empty 2>/dev/null || true
    git push -u origin main 2>/dev/null || git push -u origin master 2>/dev/null || echo "  Push may have failed — check repo"
    echo "  Pushed to $repo_name"
  fi
}

# Step 1: Create all repos
echo "=== Creating GitHub Repositories ==="
for repo in "${REPOS[@]}"; do
  case "$repo" in
    heidegger-distill)
      create_repo "$repo" "Martin Heidegger distilled persona — philosopher of Being, Dasein, Gestell"
      ;;
    marcuse-distill)
      create_repo "$repo" "Herbert Marcuse distilled persona — philosopher of one-dimensionality and the Great Refusal"
      ;;
    anders-distill)
      create_repo "$repo" "Günther Anders distilled persona — philosopher of the Promethean Gap and human obsolescence"
      ;;
    marx-distill)
      create_repo "$repo" "Karl Marx distilled persona — philosopher of alienation and class struggle"
      ;;
    philosophers-distiller)
      create_repo "$repo" "Framework for distilling historical philosopher personas into AI agents"
      ;;
  esac
  echo ""
done

# Step 2: Push philosopher files to their repos
echo "=== Pushing Files to Repositories ==="

for philosopher in heidegger marcuse anders marx; do
  repo_name="${philosopher}-distill"
  source_dir="$BASE_DIR/output/$philosopher"
  push_to_repo "$repo_name" "$source_dir"
  echo ""
done

# Step 3: Push framework files
echo "=== Pushing Framework ==="
push_to_repo "philosophers-distiller" "$FRAMEWORK_DIR"
echo ""

echo "=== Done ==="
echo "Repositories created:"
for repo in "${REPOS[@]}"; do
  echo "  https://github.com/$REPO_OWNER/$repo"
done
