#!/usr/bin/env bash
# MoltBook Collection Agent - One-Command Installer
set -e

AGENT_DIR="${HOME}/.openclaw/skills/moltbook-collection-agent"
REPO_URL="https://github.com/stonestorm2024/moltbook-collection-agent.git"

echo "📮 Installing MoltBook Collection Agent..."
echo

# Clone or update repo
if [ -d "$AGENT_DIR/.git" ]; then
    echo "→ Updating existing installation..."
    cd "$AGENT_DIR"
    git pull origin main
else
    echo "→ Cloning repository..."
    mkdir -p "$(dirname "$AGENT_DIR")"
    git clone "$REPO_URL" "$AGENT_DIR"
    cd "$AGENT_DIR"
fi

# Install Python dependencies
echo "→ Installing Python dependencies..."
pip install requests --quiet

# Create data directories
echo "→ Creating data directories..."
mkdir -p "$AGENT_DIR/data"
mkdir -p "$AGENT_DIR/logs"

# Verify credentials file exists
CRED_FILE="${HOME}/.config/moltbook/credentials.json"
if [ ! -f "$CRED_FILE" ]; then
    echo
    echo "⚠️  No MoltBook credentials found at: $CRED_FILE"
    echo "   Create it with: mkdir -p ~/.config/moltbook"
    echo '   echo '"'"'{"api_key": "moltbook_sk_xxx"}'"'"' > ~/.config/moltbook/credentials.json'
fi

echo
echo "✅ Installation complete!"
echo
echo "Next steps:"
echo "  1. Add your MoltBook API key to $CRED_FILE"
echo "  2. Run: cd $AGENT_DIR && python3 agent.py run"
echo "  3. Schedule collections: python3 scheduler.py install '0 9 * * *' daily"
echo