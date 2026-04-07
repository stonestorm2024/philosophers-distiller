---
name: moltbook-ops-manager
description: >
  Operations Manager Agent for the MoltBook Collection system.
  Manages collection runs, monitors health, publishes to GitHub/ClawHub,
  generates operational reports, and maintains the collection agent lifecycle.
  Use when: checking collection status, triggering runs, publishing updates,
  monitoring health, generating ops reports, or managing the collection agent skill.
emoji: 🎛️
tags: [operations, management, monitoring, moltbook, automation, github, clawhub]
license: MIT
author: stonestorm2024
version: 1.0.0
language: en
homepage: https://github.com/stonestorm2024/moltbook-ops-manager
claws: 500
requires:
  - python3 >= 3.9
  - gh (GitHub CLI)
  - cron
---

# MoltBook Ops Manager

Dedicated operations agent that manages the MoltBook collection agent lifecycle.

## Managed Services

| Service | Type | Description |
|---------|------|-------------|
| `moltbook-collection-agent` | Collection Agent | Collects posts/comments from MoltBook |
| `moltbook-collection-agent` | ClawHub Skill | Distributable skill package |

## Managed Repos

| Repo | Purpose |
|------|---------|
| `stonestorm2024/moltbook-collection-agent` | Collection agent source |
| `stonestorm2024/moltbook-ops-manager` | Ops manager source |
| `stonestorm2024/clawhub-moltbook` | ClawHub landing page |

## Operations

### Collection Management
```bash
# Trigger full collection run
python3 agent.py run --mode full

# Check collection status
python3 agent.py status

# Sync data to GitHub
python3 agent.py sync

# View latest results
python3 agent.py results
```

### Health Monitoring
- Collection run frequency
- API error rates
- GitHub sync status
- ClawHub download count

### Publishing Workflow
1. Collect and enrich data locally
2. Run tests / validation
3. Tag release version
4. Push to GitHub
5. Publish/updated to ClawHub
6. Announce to user

### Scheduled Operations
| Time (Beijing) | Task |
|---------------|------|
| 08:00 | Morning health check + collection |
| 16:00 | Full collection run |
| 21:00 | Evening sync + report |

## Architecture

```
User / Cron
    ↓
Ops Manager (moltbook-ops-manager)
    ↓
├── Collection Agent (moltbook-collection-agent)
│       ↓
│   MoltBook API
│       ↓
│   data/ → enriched/ → reports/
│
├── GitHub Sync
│   stonestorm2024/moltbook-collection-agent
│
└── ClawHub Publish
    moltbook-collection-agent skill
```

## Reporting

### Daily Ops Report
- Collections run: N
- Posts collected: N
- Comments gathered: N
- Errors: N
- GitHub sync: ✅/❌
- ClawHub status: version N

### Health Metrics
- API success rate: XX%
- Avg response time: Xms
- Last successful collection: HH:MM
- Streak: N days

## CLI Usage

```bash
# Run ops manager
python3 agent.py ops --task [health|collect|report|publish|all]

# Health check
python3 agent.py ops --task health

# Full ops cycle
python3 agent.py ops --task all

# Publish update to ClawHub
python3 agent.py ops --task publish --version 1.0.1
```