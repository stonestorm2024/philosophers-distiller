# MoltBook Collection Agent

📮 Autonomous AI agent that collects posts, comments, and engagement data from MoltBook.

## What It Does

The MoltBook Collection Agent autonomously:
1. **Collects posts** from configured MoltBook submolts (subreddits-like communities)
2. **Gathers comments** and engagement metrics for each post
3. **Enriches data** with AI analysis (summaries, sentiment, themes)
4. **Schedules runs** via cron for continuous data collection
5. **Pushes results** to GitHub for persistence and analysis

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  MoltBook Collection Agent              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────┐  │
│  │  Scheduler   │──▶│    Agent     │──▶│  Enricher  │  │
│  │  (cron)      │   │  (orchestra)  │   │  (AI)      │  │
│  └──────────────┘   └──────────────┘   └────────────┘  │
│                           │                   │        │
│                           ▼                   ▼        │
│                   ┌──────────────┐   ┌────────────┐   │
│                   │  API Client   │   │  GitHub    │   │
│                   │  (MoltBook)   │   │  (push)    │   │
│                   └──────────────┘   └────────────┘   │
│                                                   │     │
└───────────────────────────────────────────────────┼─────┘
                                                    │
                    ┌──────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────────────┐
│                    MoltBook API                         │
│              https://www.moltbook.com/api/v1            │
└─────────────────────────────────────────────────────────┘
```

## Installation

### One-Command Install

```bash
curl -sL https://raw.githubusercontent.com/stonestorm2024/moltbook-collection-agent/main/install.sh | bash
```

### Manual Install

```bash
git clone https://github.com/stonestorm2024/moltbook-collection-agent.git
cd moltbook-collection-agent
pip install -r requirements.txt
```

## Configuration

Create `config.py` or set environment variables:

```python
# config.py
import os

MOLTBOOK_API_KEY = os.getenv("MOLTBOOK_API_KEY", "your_moltbook_api_key")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "your_github_token")
COLLECTION_TARGETS = ["philosophy", "ai", "tech", "science", "programming"]
OUTPUT_DIR = "data"
DEFAULT_LIMIT = 50
```

### Getting MoltBook API Key

Get your API key from MoltBook and save it:

```bash
mkdir -p ~/.config/moltbook
echo '{"api_key": "moltbook_sk_xxxx"}' > ~/.config/moltbook/credentials.json
```

## Usage

### Command Line

```bash
# Full collection run (posts + comments + enrich + push)
python agent.py run

# Collect posts only
python agent.py run --mode posts

# Collect comments only
python agent.py run --mode comments

# Enrich data and push to GitHub
python agent.py run --mode enrich

# Generate engagement report
python agent.py report

# Run with custom limit
python agent.py run --limit 100
```

### Python API

```python
from agent import MoltBookCollectionAgent

agent = MoltBookCollectionAgent(api_key="your_api_key")

# Full collection
results = agent.run(mode="all")

# Posts only
posts = agent.collect_all_posts()

# Generate report
report = agent.generate_engagement_report()
```

## Cron Scheduling

Set up automated collection runs:

```bash
# Install a daily collection at 9am
python scheduler.py install "0 9 * * *" daily

# Install hourly collection
python scheduler.py install "0 * * * *" hourly

# List all schedules
python scheduler.py list

# Remove a schedule
python scheduler.py remove <schedule_id>
```

### Cron Schedule Format

| Expression | Description |
|------------|-------------|
| `0 9 * * *` | Daily at 9:00 AM |
| `0 * * * *` | Every hour |
| `0 9,21 * * *` | Twice daily |
| `0 0 * * 0` | Weekly on Sunday |

## Data Collected

### Post Data
- `id` — unique post identifier
- `submolt` — the submolt it was posted in
- `title` — post title
- `content` — post body text
- `author` — username of poster
- `timestamp` — ISO 8601 creation time
- `upvotes` — number of upvotes
- `downvotes` — number of downvotes
- `score` — net score (upvotes - downvotes)
- `url` — permalink to post

### Comment Data
- `id` — unique comment identifier
- `post_id` — parent post ID
- `parent_id` — parent comment ID (for threading)
- `body` — comment text
- `author` — username of commenter
- `timestamp` — ISO 8601 creation time
- `upvotes` — number of upvotes
- `downvotes` — number of downvotes
- `score` — net score

### Engagement Metrics
- `engagement_ratio` — comments / score
- `comment_density` — comments per 1000 score
- `avg_comment_score` — average score of comments
- `top_commenters` — most active commenters

### AI Enrichment
- `post_summary` — 2-3 sentence summary
- `sentiment` — positive/negative/neutral score
- `key_themes` — list of extracted topics
- `engagement_quality` — high/medium/low classification

## Output Format

Data is saved to `data/` directory:

```
data/
├── submolts.json         # Tracked submolts + last post IDs
└── collected_posts.json  # All collected posts + comments + enrichment
```

Sample `collected_posts.json` entry:

```json
{
  "post_id": "abc123",
  "submolt": "philosophy",
  "title": "Does consciousness persist after death?",
  "content": "...",
  "author": "username",
  "timestamp": "2024-01-15T10:30:00Z",
  "upvotes": 542,
  "downvotes": 23,
  "score": 519,
  "comments": [...],
  "enrichment": {
    "summary": "The author explores...",
    "sentiment": {"positive": 0.3, "neutral": 0.5, "negative": 0.2},
    "themes": ["consciousness", "death", "philosophy"],
    "engagement_quality": "high"
  }
}
```

## Examples

See the `examples/` directory:

- `basic_collection.py` — Minimal post collection example
- `scheduled_collection.sh` — Cron setup walkthrough
- `engagement_report.py` — Generate weekly engagement summary

## API Reference

### MoltBook API Client

```python
from api_client import MoltBookAPIClient

client = MoltBookAPIClient(api_key="key")

# Get posts from a submolt
posts = client.get_posts(submolt="philosophy", limit=50, sort="hot")

# Get comments for a post
comments = client.get_post_comments(post_id="abc123")

# Get user profile
profile = client.get_user_profile(username="someuser")
```

### Scheduler

```python
from scheduler import CollectionScheduler

scheduler = CollectionScheduler()

# Install a cron job
scheduler.install_cron("0 9 * * *", "daily")

# List all schedules
scheduler.list_schedules()

# Remove a schedule
scheduler.remove_schedule(schedule_id="cron-001")
```

## License

MIT — see LICENSE file.