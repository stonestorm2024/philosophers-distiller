#!/usr/bin/env python3
"""
MoltBook Collection Agent
Collects posts, comments, and engagement data from MoltBook.
Schedules collection runs and enriches data with AI analysis.
"""
import os
import sys
import json
import logging
import argparse
import base64
import subprocess
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Any, Optional

from config import (
    MOLTBOOK_API_KEY, GITHUB_TOKEN, GITHUB_REPO,
    COLLECTION_TARGETS, DEFAULT_LIMIT, OUTPUT_DIR,
    SUBMOLTS_FILE, COLLECTED_POSTS_FILE,
)
from api_client import MoltBookAPIClient, MoltBookAPIError
from enricher import DataEnricher
from scheduler import CollectionScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class MoltBookCollectionAgent:
    """
    Autonomous agent for collecting and enriching MoltBook data.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or MOLTBOOK_API_KEY
        if not self.api_key:
            raise ValueError("No MoltBook API key provided. Set MOLTBOOK_API_KEY env var or pass api_key.")
        self.client = MoltBookAPIClient(self.api_key)
        self.enricher = DataEnricher()
        self.scheduler = CollectionScheduler()
        self.output_dir = Path(OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)

    # ───────────────────────────────────────────────────────────
    # Data loading / saving
    # ───────────────────────────────────────────────────────────

    def _load_json(self, path: Path) -> Any:
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None

    def _save_json(self, path: Path, data: Any):
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_submolts(self) -> Dict[str, Any]:
        return self._load_json(SUBMOLTS_FILE) or {"submolts": {}, "last_sync": None}

    def _save_submolts(self, data: Dict[str, Any]):
        self._save_json(SUBMOLTS_FILE, data)

    def _load_collected_posts(self) -> List[Dict[str, Any]]:
        return self._load_json(COLLECTED_POSTS_FILE) or []

    def _save_collected_posts(self, posts: List[Dict[str, Any]]):
        self._save_json(COLLECTED_POSTS_FILE, posts)

    # ───────────────────────────────────────────────────────────
    # Collection methods
    # ───────────────────────────────────────────────────────────

    def collect_posts(self, submolt: str, limit: int = DEFAULT_LIMIT) -> List[Dict[str, Any]]:
        """
        Collect posts from a single submolt.
        
        Returns posts with basic metadata, excluding comments.
        """
        try:
            posts = self.client.get_posts(submolt=submolt, limit=limit, sort="hot")
            return posts
        except MoltBookAPIError as e:
            logger.error(f"Failed to collect posts from /{submolt}: {e}")
            return []

    def collect_comments(self, post_id: str) -> List[Dict[str, Any]]:
        """Collect all comments for a given post."""
        try:
            return self.client.get_post_comments(post_id, limit=200)
        except MoltBookAPIError as e:
            logger.error(f"Failed to collect comments for post {post_id}: {e}")
            return []

    def collect_all_posts(self) -> List[Dict[str, Any]]:
        """
        Collect posts from all configured submolts.
        
        Tracks which posts are new vs already-collected.
        """
        submolts_data = self._load_submolts()
        all_posts = []
        seen_ids = set()

        for submolt in COLLECTION_TARGETS:
            logger.info(f"Collecting posts from /{submolt}...")
            posts = self.collect_posts(submolt, limit=DEFAULT_LIMIT)

            # Track newest post ID for this submolt
            if posts:
                submolts_data["submolts"][submolt] = {
                    "last_post_id": posts[0].get("id"),
                    "last_sync": datetime.utcnow().isoformat() + "Z",
                }

            for post in posts:
                pid = post.get("id")
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    post["_submolt"] = submolt
                    all_posts.append(post)

            logger.info(f"  → Collected {len(posts)} posts from /{submolt}")

        submolts_data["last_sync"] = datetime.utcnow().isoformat() + "Z"
        self._save_submolts(submolts_data)
        logger.info(f"Total new posts collected: {len(all_posts)}")
        return all_posts

    def collect_all_comments(self) -> Dict[str, List[Dict[str, Any]]]:
        """Collect comments for all previously collected posts."""
        collected = self._load_collected_posts()
        existing_ids = {item["post"]["id"] for item in collected if "post" in item}

        # Collect for new posts only
        submolts_data = self._load_submolts()
        all_comments: Dict[str, List[Dict[str, Any]]] = {}

        for submolt, info in submolts_data.get("submolts", {}).items():
            last_pid = info.get("last_post_id")
            if not last_pid:
                continue
            try:
                comments = self.collect_comments(last_pid)
                all_comments[last_pid] = comments
                logger.info(f"  → {len(comments)} comments for post {last_pid}")
            except Exception as e:
                logger.warning(f"Could not get comments for {last_pid}: {e}")

        return all_comments

    # ───────────────────────────────────────────────────────────
    # Enrichment
    # ───────────────────────────────────────────────────────────

    def enrich_with_ai(
        self,
        posts: Optional[List[Dict[str, Any]]] = None,
        comments_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Enrich collected posts with AI analysis.
        
        If posts is None, loads from COLLECTED_POSTS_FILE.
        """
        if posts is None:
            collected = self._load_collected_posts()
            posts = [item.get("post", item) for item in collected]

        enriched = []
        for post in posts:
            pid = post.get("id")
            comments = (comments_map or {}).get(pid, [])
            enrichment = self.enricher.enrich_post(post, comments)
            enriched.append({
                "post": post,
                "comments": comments,
                "enrichment": enrichment,
                "collected_at": datetime.utcnow().isoformat() + "Z",
            })

        logger.info(f"Enriched {len(enriched)} posts")
        return enriched

    # ───────────────────────────────────────────────────────────
    # GitHub push
    # ───────────────────────────────────────────────────────────

    def push_to_github(self, data: List[Dict[str, Any]], force: bool = False):
        """
        Push collected data to the GitHub repo via Contents API.
        
        Updates data/collected_posts.json in the repo.
        """
        logger.info("Pushing data to GitHub...")
        content = json.dumps(data, indent=2, ensure_ascii=False)

        # Get current SHA of file in repo (if exists)
        sha = None
        if not force:
            result = subprocess.run(
                [
                    "curl", "-s", "-H", f"Authorization: Bearer {GITHUB_TOKEN}",
                    f"https://api.github.com/repos/{GITHUB_REPO}/contents/data/collected_posts.json",
                ],
                capture_output=True, text=True,
            )
            try:
                resp = json.loads(result.stdout)
                sha = resp.get("sha")
            except Exception:
                pass

        self._github_put(
            path="data/collected_posts.json",
            content=content,
            message=f"chore: update collected posts {datetime.utcnow().isoformat()[:10]}",
            sha=sha,
        )

        # Also push submolts.json
        submolts = self._load_submolts()
        sha = None
        result = subprocess.run(
            [
                "curl", "-s", "-H", f"Authorization: Bearer {GITHUB_TOKEN}",
                f"https://api.github.com/repos/{GITHUB_REPO}/contents/data/submolts.json",
            ],
            capture_output=True, text=True,
        )
        try:
            resp = json.loads(result.stdout)
            sha = resp.get("sha")
        except Exception:
            pass

        self._github_put(
            path="data/submolts.json",
            content=json.dumps(submolts, indent=2),
            message=f"chore: update submolts {datetime.utcnow().isoformat()[:10]}",
            sha=sha,
        )

        logger.info("GitHub push complete")

    def _github_put(self, path: str, content: str, message: str, sha: Optional[str] = None):
        """Put a file to GitHub via Contents API."""
        import urllib.request

        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
        payload = json.dumps({
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "sha": sha,
        }).encode()

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Content-Type": "application/json",
            },
            method="PUT",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                logger.info(f"  → Pushed {path}: {result.get('commit', {}).get('sha', '')[:7]}")
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            logger.error(f"GitHub API error for {path}: {e.code} {body}")

    # ───────────────────────────────────────────────────────────
    # Reports
    # ───────────────────────────────────────────────────────────

    def generate_engagement_report(self) -> Dict[str, Any]:
        """
        Generate a weekly engagement summary report.
        """
        collected = self._load_collected_posts()
        if not collected:
            return {"error": "No collected posts found"}

        today = date.today()
        week_ago = datetime.combine(today, datetime.min.time()).timestamp()

        # Filter posts from last 7 days
        recent = []
        for item in collected:
            post = item.get("post", item)
            ts_str = post.get("timestamp", "")
            try:
                if ts_str:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
                    if ts >= week_ago:
                        recent.append(item)
            except Exception:
                pass

        if not recent:
            return {"error": "No posts from the last 7 days"}

        # Aggregate stats
        total_posts = len(recent)
        total_comments = sum(len(item.get("comments", [])) for item in recent)
        total_score = sum(item.get("post", {}).get("score", 0) for item in recent)
        total_upvotes = sum(item.get("post", {}).get("upvotes", 0) for item in recent)

        quality_counts = {"high": 0, "medium": 0, "low": 0}
        themes: Dict[str, int] = {}
        sentiments = {"positive": 0.0, "neutral": 0.0, "negative": 0.0}

        for item in recent:
            enr = item.get("enrichment", {})
            quality = enr.get("engagement_quality", "low")
            quality_counts[quality] = quality_counts.get(quality, 0) + 1

            for theme in enr.get("themes", []):
                themes[theme] = themes.get(theme, 0) + 1

            sent = enr.get("sentiment", {})
            for k, v in sent.items():
                sentiments[k] += v

        # Average sentiment
        n = total_posts
        for k in sentiments:
            sentiments[k] = round(sentiments[k] / n, 3)

        top_themes = sorted(themes.items(), key=lambda x: -x[1])[:10]

        report = {
            "report_date": datetime.utcnow().isoformat() + "Z",
            "period": "last_7_days",
            "total_posts": total_posts,
            "total_comments": total_comments,
            "total_score": total_score,
            "total_upvotes": total_upvotes,
            "engagement_quality": quality_counts,
            "top_themes": [{"theme": t, "count": c} for t, c in top_themes],
            "avg_sentiment": sentiments,
            "avg_comments_per_post": round(total_comments / total_posts, 1),
            "avg_score_per_post": round(total_score / total_posts, 1),
        }

        logger.info(f"Generated engagement report: {total_posts} posts, {total_comments} comments")
        return report

    # ───────────────────────────────────────────────────────────
    # Scheduled collection
    # ───────────────────────────────────────────────────────────

    def run_scheduled_collection(self, schedule_id: Optional[str] = None):
        """Run a full collection cycle, optionally updating schedule metadata."""
        logger.info(f"Starting scheduled collection (schedule_id={schedule_id})")
        try:
            posts = self.collect_all_posts()
            comments_map = self.collect_all_comments()
            enriched = self.enrich_with_ai(posts, comments_map)

            # Merge with existing collected posts
            existing = self._load_collected_posts()
            existing_ids = {item["post"]["id"] for item in existing if "post" in item}
            merged = existing.copy()
            for item in enriched:
                pid = item["post"]["id"]
                if pid not in existing_ids:
                    merged.append(item)

            self._save_collected_posts(merged)
            self.push_to_github(merged)

            if schedule_id:
                self.scheduler.update_last_run(schedule_id)

            logger.info("Scheduled collection complete")
            return enriched
        except Exception as e:
            logger.error(f"Scheduled collection failed: {e}")
            raise

    # ───────────────────────────────────────────────────────────
    # Full collection run
    # ───────────────────────────────────────────────────────────

    def full_collection(self) -> List[Dict[str, Any]]:
        """
        Complete collection pipeline:
        1. Collect posts from all submolts
        2. Collect comments for new posts
        3. Enrich with AI
        4. Save locally
        5. Push to GitHub
        """
        logger.info("=== Full Collection Run ===")
        posts = self.collect_all_posts()
        comments_map = self.collect_all_comments()
        enriched = self.enrich_with_ai(posts, comments_map)

        # Save locally
        self._save_collected_posts(enriched)

        # Push to GitHub
        self.push_to_github(enriched)

        logger.info(f"=== Collection Complete: {len(enriched)} posts enriched ===")
        return enriched

    def run(self, mode: str = "all") -> List[Dict[str, Any]]:
        """
        Run the agent in the specified mode.
        
        Modes:
          all     - Full pipeline (posts + comments + enrich + push)
          posts   - Collect posts only
          comments - Collect comments for existing posts
          enrich  - Enrich existing collected posts
          report  - Generate and print engagement report
        """
        if mode == "all":
            return self.full_collection()
        elif mode == "posts":
            return self.collect_all_posts()
        elif mode == "comments":
            return self.collect_all_comments()
        elif mode == "enrich":
            enriched = self.enrich_with_ai()
            self._save_collected_posts(enriched)
            self.push_to_github(enriched)
            return enriched
        elif mode == "report":
            report = self.generate_engagement_report()
            print(json.dumps(report, indent=2))
            return report
        else:
            raise ValueError(f"Unknown mode: {mode}")


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

def main(argv: List[str]):
    parser = argparse.ArgumentParser(
        description="MoltBook Collection Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "command", nargs="?", default="run",
        choices=["run", "report"],
        help="Command to run"
    )
    parser.add_argument("--mode", default="all",
                        choices=["all", "posts", "comments", "enrich"],
                        help="Collection mode (default: all)")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help="Max posts per submolt")
    parser.add_argument("--api-key", help="MoltBook API key (overrides env)")
    parser.add_argument("--schedule-id", help="Schedule ID for scheduled runs")
    parser.add_argument("--push", action="store_true", default=True,
                        help="Push to GitHub after collection")
    parser.add_argument("--no-push", dest="push", action="store_false",
                        help="Skip GitHub push")

    args = parser.parse_args(argv)

    agent = MoltBookCollectionAgent(api_key=args.api_key)

    if args.command == "report":
        report = agent.generate_engagement_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        result = agent.run(mode=args.mode)
        print(f"Collection complete. {len(result)} items processed.")


if __name__ == "__main__":
    main(sys.argv[1:])