#!/usr/bin/env python3
"""
Basic Collection Example
Minimal example of collecting posts from MoltBook.
"""
import sys
sys.path.insert(0, "..")

from api_client import MoltBookAPIClient
from config import MOLTBOOK_API_KEY

# Initialize client
client = MoltBookAPIClient(api_key=MOLTBOOK_API_KEY)

# Check connection
if not client.health_check():
    print("⚠️  Could not connect to MoltBook API. Check your API key.")
    sys.exit(1)

# Collect posts from philosophy submolt
print("Fetching posts from /philosophy...")
posts = client.get_posts(submolt="philosophy", limit=10, sort="hot")

print(f"\nGot {len(posts)} posts:\n")
for post in posts:
    score = post.get("score", 0)
    title = post.get("title", "Untitled")
    author = post.get("author", "unknown")
    print(f"  [{score:>4}] {title}")
    print(f"         by {author}\n")