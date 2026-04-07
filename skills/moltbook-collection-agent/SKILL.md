---
name: moltbook-collection-agent
description: >
  MoltBook Autonomous Collection Agent — continuously monitors and collects posts,
  comments, and engagement data from MoltBook across configurable submolts.
  Schedules collection runs, enriches data with AI analysis, and syncs to GitHub.
emoji: 📮
tags: [moltbook, collection, agent, scheduled-tasks, social-data, engagement]
license: MIT
author: stonestorm2024
version: 1.0.0
language: en
homepage: https://github.com/stonestorm2024/moltbook-collection-agent
claws: 1000
requires:
  - python3 >= 3.9
  - requests
  - gh (GitHub CLI)
  - cron
---

# MoltBook Collection Agent

Autonomous AI agent for continuous MoltBook data collection.

## What It Does

| Function | Description |
|----------|-------------|
| `collect_posts` | Collect new posts from configured submolts |
| `collect_comments` | Gather comments and engagement metrics for each post |
| `enrich` | AI-powered theme extraction and sentiment analysis |
| `report` | Generate engagement reports |
| `sync` | Push data to GitHub |
| `schedule` | Set up cron-based collection runs |

## Installation

```bash
# Install skill
openclaw skills install moltbook-collection-agent

# Or from source
git clone https://github.com/stonestorm2024/moltbook-collection-agent.git
cd moltbook-collection-agent
bash install.sh
```

## Configuration

Set credentials in `~/.config/moltbook/credentials.json`:

```json
{
  "api_key": "moltbook_sk_YOUR_KEY_HERE"
}
```

GitHub token (Fine-Grained PAT with repo read/write permissions) in environment:

```bash
export GH_PUSH_TOKEN="github_pat_..."
```

## Usage

```bash
# Run full collection cycle
python3 agent.py run --mode full

# Collect posts only
python3 agent.py run --mode posts

# Collect comments for tracked posts
python3 agent.py run --mode comments

# Enrich and generate report
python3 agent.py run --mode enrich

# Install collection schedule
python3 scheduler.py install --schedule "0 8,16 * * *"
```

## Schedule

Recommended cron (Beijing time):
- **08:00** — Morning collection
- **16:00** — Afternoon collection  
- **21:00** — Evening sync

## Architecture

```
MoltBook API
    ↓
api_client.py (data fetching)
    ↓
agent.py (orchestration)
    ↓
enricher.py (AI analysis)
    ↓
GitHub (data persistence)
```

## Data Collected

Per post:
- Title, content, author, timestamp
- Upvotes, comments count
- Verification status
- Comment threads (author, karma, content)

Per collection run:
- New posts discovered
- Engagement deltas
- Theme analysis
- Quality score

## Output

Collected data stored in `data/` directory:
- `posts.json` — all collected posts
- `comments.json` — all comments
- `enriched/` — AI-analyzed reports
- `reports/` — engagement summaries