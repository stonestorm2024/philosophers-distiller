#!/usr/bin/env python3
"""
MoltBook API Client
Wraps the MoltBook REST API for posts, comments, and user profiles.
"""
import requests
import time
import logging
from typing import List, Dict, Optional, Any
from config import MOLTBOOK_API_KEY, MOLTBOOK_BASE_URL, MAX_COMMENTS_PER_POST

logger = logging.getLogger(__name__)


class MoltBookAPIError(Exception):
    """Raised when the MoltBook API returns an error."""
    pass


class VerificationChallengeError(MoltBookAPIError):
    """Raised when a verification challenge (math problem) is required."""
    def __init__(self, challenge: Dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.challenge = challenge


class MoltBookAPIClient:
    """Client for interacting with the MoltBook API."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or MOLTBOOK_API_KEY
        self.base_url = base_url or MOLTBOOK_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "MoltBook-Collection-Agent/1.0",
        })
        self._rate_limit_remaining = float("inf")
        self._rate_limit_reset = 0

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request with rate limiting and error handling."""
        url = f"{self.base_url}/{path.lstrip('/')}"

        # Respect rate limits
        now = time.time()
        if now < self._rate_limit_reset:
            sleep_time = self._rate_limit_reset - now
            logger.info(f"Rate limited, sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)

        resp = self.session.request(method, url, **kwargs)

        # Track rate limits from headers
        if "X-RateLimit-Remaining" in resp.headers:
            self._rate_limit_remaining = int(resp.headers["X-RateLimit-Remaining"])
        if "X-RateLimit-Reset" in resp.headers:
            self._rate_limit_reset = int(resp.headers["X-RateLimit-Reset"])

        if resp.status_code == 429:
            logger.warning("Rate limit hit, backing off")
            self._rate_limit_reset = time.time() + 60
            time.sleep(60)
            return self._request(method, path, **kwargs)

        if resp.status_code == 402:
            # Verification challenge required
            try:
                data = resp.json()
                raise VerificationChallengeError(
                    data.get("challenge", {}),
                    "Verification challenge required"
                )
            except ValueError:
                raise MoltBookAPIError(f"HTTP 402: {resp.text}")

        if not resp.ok:
            raise MoltBookAPIError(f"HTTP {resp.status_code}: {resp.text}")

        return resp.json()

    def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """Make a GET request."""
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> Dict[str, Any]:
        """Make a POST request."""
        return self._request("POST", path, **kwargs)

    # ───────────────────────────────────────────────────────────
    # Posts
    # ───────────────────────────────────────────────────────────

    def get_posts(
        self,
        submolt: str,
        limit: int = 50,
        sort: str = "hot",
        after: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch posts from a submolt.

        Args:
            submolt: Submolt name (e.g., 'philosophy', 'ai')
            limit: Number of posts to fetch (max 100)
            sort: Sort order - 'hot', 'new', 'top', 'rising'
            after: Cursor for pagination (post ID)

        Returns:
            List of post objects
        """
        params = {"limit": min(limit, 100), "sort": sort}
        if after:
            params["after"] = after

        data = self.get(f"submolts/{submolt}/posts", params=params)
        posts = data.get("posts", [])

        logger.info(f"Fetched {len(posts)} posts from /{submolt}")
        return posts

    def get_post(self, post_id: str) -> Dict[str, Any]:
        """Get a single post by ID."""
        return self.get(f"posts/{post_id}")

    # ───────────────────────────────────────────────────────────
    # Comments
    # ───────────────────────────────────────────────────────────

    def get_post_comments(
        self,
        post_id: str,
        limit: int = MAX_COMMENTS_PER_POST,
        sort: str = "best",
    ) -> List[Dict[str, Any]]:
        """
        Fetch comments for a post.

        Args:
            post_id: The post's unique ID
            limit: Max comments to fetch
            sort: Sort order - 'best', 'new', 'top', 'controversial'

        Returns:
            Flat list of comment objects
        """
        params = {"limit": min(limit, MAX_COMMENTS_PER_POST), "sort": sort}
        data = self.get(f"posts/{post_id}/comments", params=params)
        comments = data.get("comments", [])

        logger.info(f"Fetched {len(comments)} comments for post {post_id}")
        return comments

    # ───────────────────────────────────────────────────────────
    # Users
    # ───────────────────────────────────────────────────────────

    def get_user_profile(self, username: str) -> Dict[str, Any]:
        """Get a user's public profile."""
        return self.get(f"users/{username}")

    def get_user_posts(
        self,
        username: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get posts by a specific user."""
        params = {"limit": min(limit, 100)}
        data = self.get(f"users/{username}/posts", params=params)
        return data.get("posts", [])

    # ───────────────────────────────────────────────────────────
    # Utility
    # ───────────────────────────────────────────────────────────

    def health_check(self) -> bool:
        """Check if the API is reachable and credentials are valid."""
        try:
            self.get("me")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False