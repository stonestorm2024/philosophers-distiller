#!/usr/bin/env bash
# Scheduled Collection Setup
# Demonstrates how to install cron schedules for the MoltBook Collection Agent

AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$AGENT_DIR"

echo "=== MoltBook Collection Agent — Cron Setup ==="
echo

# Check Python is available
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

# Function to run the scheduler
run_scheduler() {
    python3 scheduler.py "$@"
}

echo "Available commands:"
echo
echo "  1. Install daily collection (9:00 AM)"
echo "  2. Install twice-daily (9 AM & 9 PM)"
echo "  3. Install hourly collection"
echo "  4. Install weekly (Sunday midnight)"
echo "  5. List all schedules"
echo "  6. Remove a schedule"
echo "  7. Run collection now (no scheduling)"
echo

read -p "Choose an option [1-7]: " choice

case $choice in
    1)
        echo "Installing daily collection at 9:00 AM..."
        run_scheduler install "0 9 * * *" daily
        ;;
    2)
        echo "Installing twice-daily collection..."
        run_scheduler install "0 9,21 * * *" daily
        ;;
    3)
        echo "Installing hourly collection..."
        run_scheduler install "0 * * * *" hourly
        ;;
    4)
        echo "Installing weekly collection (Sunday midnight)..."
        run_scheduler install "0 0 * * 0" weekly
        ;;
    5)
        echo "Current schedules:"
        run_scheduler list
        ;;
    6)
        echo "Current schedules:"
        run_scheduler list
        echo
        read -p "Enter schedule ID to remove: " sid
        run_scheduler remove "$sid"
        ;;
    7)
        echo "Running collection now..."
        python3 agent.py run
        ;;
    *)
        echo "Invalid option"
        ;;
esac