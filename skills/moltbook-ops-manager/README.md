# MoltBook Ops Manager

Operations manager for the MoltBook Collection system.

## What It Does

| Task | Description |
|------|-------------|
| `ops --task health` | Health check on collection agent + GitHub sync |
| `ops --task collect` | Trigger full collection run |
| `ops --task report` | Generate ops report (JSON + Markdown) |
| `ops --task publish` | Publish collection agent to GitHub + ClawHub |
| `ops --task all` | Full ops cycle: health → collect → report → publish |

## Architecture

```
┌─────────────────────────────────────────────┐
│        MoltBook Ops Manager                  │
│        moltbook-ops-manager                  │
└─────────────────┬───────────────────────────┘
                  │
      ┌───────────┼───────────┐
      ↓           ↓           ↓
┌──────────┐ ┌──────────┐ ┌──────────┐
│Collection│ │ GitHub   │ │ ClawHub  │
│ Agent    │ │ Sync     │ │ Publish  │
└────┬─────┘ └────┬─────┘ └────┬─────┘
     ↓             ↓            ↓
MoltBook API   stonestorm2024  clawhub.ai/
               /moltbook-      moltbook-
               collection-agent collection-agent
```

## Quick Start

```bash
# Health check
python3 agent.py ops --task health

# Full ops cycle
python3 agent.py ops --task all

# Publish new version
python3 agent.py publish --version 1.0.1
```

## Crontab Setup

```bash
# Morning health check (08:00 Beijing)
0 8 * * * cd /home/admin/.openclaw/workspace-trading/moltbook-ops-manager && python3 agent.py ops --task health >> output/cron.log 2>&1

# Full collection + report (16:00 Beijing)
0 16 * * * cd /home/admin/.openclaw/workspace-trading/moltbook-ops-manager && python3 agent.py ops --task all >> output/cron.log 2>&1
```

## Output

- `output/ops_report_YYYYMMDD_HHMM.json` — structured ops report
- `output/ops_report_YYYYMMDD_HHMM.md` — human-readable report
- `output/latest_report.json` — most recent report

## Managed Collection Agent

The ops manager controls:

**`moltbook-collection-agent`**
- Repo: `github.com/stonestorm2024/moltbook-collection-agent`
- Collects: posts, comments, engagement data from MoltBook
- Schedule: 08:00 / 16:00 / 21:00 (Beijing)
- Skill: `clawhub.ai/moltbook-collection-agent`

## Version

Current: 1.0.0