#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MoltBook Ops Manager
Manages the MoltBook collection agent lifecycle.

Usage:
    python3 agent.py ops --task [health|collect|report|publish|all]
    python3 agent.py status
    python3 agent.py publish --version X.Y.Z
"""

import argparse
import json
import os
import subprocess
import sys
import base64
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# Paths
# ============================================================
WORKDIR = Path(__file__).parent
COLLECTION_AGENT_DIR = Path("/home/admin/.openclaw/workspace-trading/moltbook-collection-agent")
OPS_OUTPUT = WORKDIR / "output"
OPS_OUTPUT.mkdir(exist_ok=True)

GH_TOKEN = os.environ.get("GH_PUSH_TOKEN", "")
GH_REPO_OWNER = "stonestorm2024"
COLLECTION_REPO = f"{GH_REPO_OWNER}/moltbook-collection-agent"
OPS_REPO = f"{GH_REPO_OWNER}/moltbook-ops-manager"
CLAWHUB_SLUG = "moltbook-collection-agent"

CREDENTIALS_FILE = os.path.expanduser("~/.config/moltbook/credentials.json")


# ============================================================
# Utils
# ============================================================

def sh(cmd, cwd=None, capture=True):
    """Run shell command."""
    kw = {"shell": True, "cwd": cwd or WORKDIR}
    if capture:
        kw["capture_output"] = True
        kw["text"] = True
    r = subprocess.run(cmd, **kw)
    return r.returncode, r.stdout, r.stderr


def gh_api(method, path, data=None, repo=None):
    """Call GitHub API."""
    import requests
    token = GH_TOKEN
    if not token:
        return None, {"error": "No GH token"}
    repo = repo or OPS_REPO
    url = f"https://api.github.com/repos/{repo}/{path}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    if method == "GET":
        r = requests.get(url, headers=headers, timeout=10)
    elif method == "POST":
        r = requests.post(url, headers=headers, json=data, timeout=10)
    elif method == "PUT":
        r = requests.put(url, headers=headers, json=data, timeout=10)
    elif method == "PATCH":
        r = requests.patch(url, headers=headers, json=data, timeout=10)
    else:
        return None, {"error": f"Unknown method {method}"}
    try:
        return r.status_code, r.json()
    except:
        return r.status_code, {"raw": r.text[:200]}


def get_collection_status():
    """Get status from collection agent."""
    status_file = COLLECTION_AGENT_DIR / "data" / "tracked_posts.json"
    if not status_file.exists():
        return None

    with open(status_file) as f:
        data = json.load(f)

    posts = data.get("posts", [])
    last_run = data.get("last_run")

    # Count comments
    comments_file = COLLECTION_AGENT_DIR / "data" / "comments.json"
    comment_count = 0
    if comments_file.exists():
        with open(comments_file) as f:
            cd = json.load(f)
            comment_count = sum(len(v.get("comments", [])) for v in cd.values())

    return {
        "posts_collected": len(posts),
        "comments_collected": comment_count,
        "last_run": last_run,
        "posts_today": sum(1 for p in posts if last_run and p.get("collected_at", "").startswith(datetime.now().strftime("%Y-%m-%d")))
    }


def get_github_sync_status():
    """Check if collection repo was recently synced."""
    status, data = gh_api("GET", "actions/runs?per_page=3", repo=COLLECTION_REPO)
    if status == 200 and isinstance(data, dict):
        runs = data.get("workflow_runs", [])
        if runs:
            latest = runs[0]
            return {
                "last_push": latest.get("created_at", ""),
                "status": latest.get("conclusion", ""),
                "run_id": latest.get("id", "")
            }
    return None


def get_collection_repo_info():
    """Get collection repo stats from GitHub."""
    status, data = gh_api("GET", "", repo=COLLECTION_REPO)
    if status == 200 and isinstance(data, dict):
        return {
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "description": data.get("description", ""),
            "language": data.get("language", ""),
            "updated": data.get("pushed_at", ""),
        }
    return {}


# ============================================================
# Tasks
# ============================================================

def task_health():
    """Run health check."""
    print("=" * 50)
    print(f"🏥 Health Check — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # Collection status
    col = get_collection_status()
    if col:
        print(f"\n📦 Collection Agent")
        print(f"   Posts collected: {col['posts_collected']}")
        print(f"   Comments gathered: {col['comments_collected']}")
        print(f"   Last run: {col['last_run'] or 'Never'}")
        if col['last_run']:
            try:
                last = datetime.fromisoformat(col['last_run'])
                ago = datetime.now() - last
                print(f"   Time since last run: {ago}")
            except:
                pass
    else:
        print("\n⚠️  Collection agent not initialized (no data found)")

    # GitHub sync
    gh_status = get_github_sync_status()
    if gh_status:
        print(f"\n🐙 GitHub Sync")
        print(f"   Last push: {gh_status['last_push']}")
        print(f"   Status: {gh_status['status']}")
    else:
        print(f"\n⚠️  GitHub sync status unknown")

    # Repo info
    repo_info = get_collection_repo_info()
    if repo_info:
        print(f"\n📊 Collection Repo Stats")
        print(f"   ⭐ Stars: {repo_info.get('stars', 0)}")
        print(f"   🍴 Forks: {repo_info.get('forks', 0)}")
        print(f"   💬 Language: {repo_info.get('language', '?')}")

    # Cron check
    _, out, _ = sh("crontab -l 2>/dev/null")
    active = [l for l in out.splitlines() if "moltbook" in l.lower()]
    if active:
        print(f"\n⏰ Active Schedules:")
        for line in active:
            print(f"   {line}")
    else:
        print(f"\n⚠️  No cron schedules found for MoltBook")

    print("\n" + "=" * 50)


def task_collect():
    """Trigger collection run."""
    print("=" * 50)
    print(f"📮 Triggering Collection Run — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    if not COLLECTION_AGENT_DIR.exists():
        print("❌ Collection agent not found at:", COLLECTION_AGENT_DIR)
        return False

    code, out, err = sh(f"cd {COLLECTION_AGENT_DIR} && python3 agent.py run --mode full")
    print(out)
    if err:
        print("STDERR:", err)

    if code == 0:
        print("\n✅ Collection run complete")
        return True
    else:
        print(f"\n❌ Collection run failed (exit {code})")
        return False


def task_report():
    """Generate ops report."""
    print("=" * 50)
    print(f"📊 Ops Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    col = get_collection_status()
    repo_info = get_collection_repo_info()
    gh_status = get_github_sync_status()

    report = {
        "generated_at": datetime.now().isoformat(),
        "collection": col,
        "github_sync": gh_status,
        "repo_stats": repo_info,
    }

    report_file = OPS_OUTPUT / f"ops_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Report saved: {report_file.name}")

    # Also save latest
    with open(OPS_OUTPUT / "latest_report.json", "w") as f:
        json.dump(report, f, indent=2)

    # Markdown summary
    md_file = OPS_OUTPUT / f"ops_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    md_lines = [
        f"# MoltBook Ops Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"## Collection Agent",
        f"- Posts collected: {col.get('posts_collected', 0) if col else 0}",
        f"- Comments gathered: {col.get('comments_collected', 0) if col else 0}",
        f"- Last run: {col.get('last_run', 'Never') if col else 'Never'}",
        "",
        f"## GitHub",
        f"- Stars: {repo_info.get('stars', 0) if repo_info else 0}",
        f"- Forks: {repo_info.get('forks', 0) if repo_info else 0}",
        f"- Last sync: {gh_status.get('last_push', '?') if gh_status else '?'}",
        "",
    ]
    md_file.write_text("\n".join(md_lines))
    print(f"📄 Markdown: {md_file.name}")
    return True


def task_publish(version=None):
    """Publish/verify collection agent on GitHub and ClawHub."""
    print("=" * 50)
    print(f"🚀 Publish Workflow — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    if not version:
        version = datetime.now().strftime("%Y.%m.%d")

    # 1. Check GitHub repo
    print("\n1️⃣  Checking GitHub repo...")
    status, data = gh_api("GET", "", repo=COLLECTION_REPO)
    if status == 200:
        print(f"   ✅ Repo exists: {COLLECTION_REPO}")
        print(f"   ⭐ Stars: {data.get('stargazers_count', 0)}")
        print(f"   🍴 Forks: {data.get('forks_count', 0)}")
    else:
        print(f"   ❌ Repo not accessible: {data.get('message', status)}")
        return False

    # 2. Check SKILL.md exists in collection agent
    skill_file = COLLECTION_AGENT_DIR / "SKILL.md"
    if skill_file.exists():
        print(f"\n2️⃣  ✅ SKILL.md found")
    else:
        print(f"\n2️⃣  ❌ SKILL.md missing — run build first")
        return False

    # 3. Try ClawHub publish
    print(f"\n3️⃣  ClawHub publish...")
    clawhub_bin = shutil.which("clawhub") or shutil.which("npx")
    if clawhub_bin:
        cmd = f"{clawhub_bin} publish {COLLECTION_AGENT_DIR} --slug {CLAWHUB_SLUG} --version {version}"
        code, out, err = sh(cmd)
        if code == 0:
            print(f"   ✅ ClawHub publish succeeded")
        else:
            print(f"   ⚠️  ClawHub publish: {err[:200]}")
    else:
        print(f"   ⚠️  clawhub CLI not found — skipping")

    # 4. Create release
    print(f"\n4️⃣  GitHub release...")
    tag = f"v{version}"
    status, data = gh_api(
        "POST", "releases",
        data={
            "tag_name": tag,
            "name": f"MoltBook Collection Agent {tag}",
            "body": f"Automated release {tag}\n\nSee SKILL.md for usage.",
            "draft": False
        },
        repo=COLLECTION_REPO
    )
    if status == 201:
        print(f"   ✅ Release {tag} created")
    elif status == 422:
        print(f"   ⚠️  Release already exists (unified diff)")
    else:
        print(f"   ⚠️  Release: {data.get('message', status)}")

    print(f"\n{'='*50}")
    print(f"✅ Publish complete — v{version}")
    print(f"   GitHub: https://github.com/{COLLECTION_REPO}")
    print(f"   ClawHub: https://clawhub.ai/{CLAWHUB_SLUG}")
    return True


def task_all():
    """Run full ops cycle."""
    task_health()
    print()
    task_collect()
    print()
    task_report()
    print()
    task_publish()


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MoltBook Ops Manager")
    sub = parser.add_subparsers(dest="command", help="Commands")

    # ops task
    p = sub.add_parser("ops", help="Run ops task")
    p.add_argument("--task", choices=["health", "collect", "report", "publish", "all"], default="all")

    # status
    sub.add_parser("status", help="Show status")

    # publish
    p2 = sub.add_parser("publish", help="Publish to GitHub/ClawHub")
    p2.add_argument("--version", default=None)

    args = parser.parse_args()

    if args.command == "ops":
        {"health": task_health, "collect": task_collect,
         "report": task_report, "publish": task_publish,
         "all": task_all}[args.task]()
    elif args.command == "status":
        task_health()
    elif args.command == "publish":
        task_publish(args.version)
    else:
        parser.print_help()