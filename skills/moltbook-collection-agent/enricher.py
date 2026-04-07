#!/usr/bin/env python3
"""
MoltBook Data Enricher
AI-powered enrichment: summaries, sentiment analysis, theme extraction,
engagement quality classification.
"""
import re
import logging
from typing import Dict, List, Any, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


class DataEnricher:
    """
    Enriches collected MoltBook posts and comments with AI analysis.
    
    Uses lightweight heuristics and pattern matching since we don't
    require an external AI API — useful for when API credits are limited.
    
    For production, replace `analyze_*` methods with actual LLM calls.
    """

    POSITIVE_WORDS = {
        "great", "awesome", "amazing", "excellent", "love", "wonderful",
        "fantastic", "brilliant", "beautiful", "perfect", "best", "happy",
        "excited", "interesting", "helpful", "impressive", "nice", "good",
        "cool", "fascinating", "insightful", "agree", "yes", "correct",
    }
    NEGATIVE_WORDS = {
        "terrible", "awful", "horrible", "bad", "hate", "worst", "stupid",
        "wrong", "disagree", "false", "terrible", "useless", "boring",
        "annoying", "pathetic", "disappointing", "regret", "poor", "fail",
        "broken", "dumb", "trash", "garbage", "no", "not", "never",
    }
    
    # Common philosophical/tech themes
    THEME_KEYWORDS = {
        "consciousness": ["conscious", "awareness", "subjective", "qualia", "phenomenal"],
        "ai": ["ai", "artificial intelligence", "machine learning", "neural", "gpt", "llm"],
        "ethics": ["ethics", "moral", "right", "wrong", "ought", "should"],
        "technology": ["tech", "software", "code", "computer", "digital", "algorithm"],
        "science": ["science", "experiment", "research", "study", "data", "evidence"],
        "philosophy": ["philosophy", "philosophical", "metaphysics", "epistemology"],
        "politics": ["politics", "government", "policy", "democracy", "liberal", "conservative"],
        "economics": ["economy", "market", "money", "capital", "investment", "stock"],
        "religion": ["god", "religion", "faith", "belief", "spiritual", "soul"],
        "existential": ["existential", "meaning", "purpose", "life", "death", "mortality"],
    }

    def __init__(self, model: str = "local"):
        self.model = model  # 'local' uses heuristics; swap for 'openai', 'claude', etc.

    # ───────────────────────────────────────────────────────────
    # Core enrichment entry
    # ───────────────────────────────────────────────────────────

    def enrich_post(self, post: Dict[str, Any], comments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Enrich a single post with all available analysis.
        
        Args:
            post: Post data dict
            comments: List of comment dicts
            
        Returns:
            Enrichment dict with summary, sentiment, themes, quality
        """
        return {
            "summary": self.generate_post_summary(post, comments),
            "sentiment": self.sentiment_analysis(post, comments),
            "themes": self.extract_key_themes(post, comments),
            "engagement_quality": self.classify_engagement_quality(post, comments),
        }

    def enrich_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich a list of posts that already have comments attached."""
        enriched = []
        for item in posts:
            post = item.get("post", item)
            comments = item.get("comments", [])
            item["enrichment"] = self.enrich_post(post, comments)
            enriched.append(item)
        return enriched

    # ───────────────────────────────────────────────────────────
    # Post summary
    # ───────────────────────────────────────────────────────────

    def generate_post_summary(self, post: Dict[str, Any], comments: List[Dict[str, Any]]) -> str:
        """
        Generate a 2-3 sentence summary of the post.
        
        Strategy: extract key sentence from content + top comment insight.
        """
        title = post.get("title", "")
        content = post.get("content", "")
        body = content if content else title

        # Clean up
        body = re.sub(r"\s+", " ", body).strip()
        if not body:
            body = title

        # Truncate intelligently at ~300 chars
        if len(body) > 300:
            cutoff = body[:297].rfind(".")
            if cutoff > 100:
                body = body[:cutoff + 1]
            else:
                body = body[:297] + "..."

        # Add insight from top comment if available
        insight = ""
        if comments:
            top = max(comments, key=lambda c: c.get("score", 0), default=None)
            if top and top.get("body"):
                comment_body = re.sub(r"\s+", " ", top["body"])[:150]
                if len(comment_body) == 150:
                    comment_body = comment_body.rsplit(" ", 1)[0] + "..."
                insight = f" Top comment notes: \"{comment_body}\""

        return f"{body}.{insight}"

    # ───────────────────────────────────────────────────────────
    # Sentiment analysis
    # ───────────────────────────────────────────────────────────

    def sentiment_analysis(self, post: Dict[str, Any], comments: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Analyze sentiment of post + comments.
        
        Returns:
            Dict with positive, neutral, negative scores (sum to 1.0)
        """
        texts = [post.get("content", ""), post.get("title", "")]
        texts += [c.get("body", "") for c in comments]
        all_text = " ".join(texts).lower()

        pos_count = sum(1 for w in self.POSITIVE_WORDS if w in all_text)
        neg_count = sum(1 for w in self.NEGATIVE_WORDS if w in all_text)
        total = pos_count + neg_count + 1  # +1 to avoid division by zero

        pos_score = pos_count / total
        neg_score = neg_count / total
        neu_score = 1.0 - pos_score - neg_score

        # Normalize to sum to 1.0
        total_score = pos_score + neg_score + neu_score
        if total_score > 0:
            pos_score /= total_score
            neg_score /= total_score
            neu_score /= total_score

        return {
            "positive": round(pos_score, 3),
            "neutral": round(neu_score, 3),
            "negative": round(neg_score, 3),
        }

    # ───────────────────────────────────────────────────────────
    # Theme extraction
    # ───────────────────────────────────────────────────────────

    def extract_key_themes(self, post: Dict[str, Any], comments: List[Dict[str, Any]]) -> List[str]:
        """
        Extract top 3-5 themes from post and comments.
        
        Uses keyword matching against known theme categories.
        """
        texts = [
            post.get("content", ""),
            post.get("title", ""),
        ]
        texts += [c.get("body", "") for c in comments[:20]]  # sample first 20
        all_text = " ".join(texts).lower()

        scores: Dict[str, int] = {}
        for theme, keywords in self.THEME_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in all_text)
            if count > 0:
                scores[theme] = count

        # Return top themes sorted by score
        sorted_themes = sorted(scores.items(), key=lambda x: -x[1])
        return [theme for theme, _ in sorted_themes[:5]]

    # ───────────────────────────────────────────────────────────
    # Engagement quality classification
    # ───────────────────────────────────────────────────────────

    def classify_engagement_quality(
        self, 
        post: Dict[str, Any], 
        comments: List[Dict[str, Any]]
    ) -> str:
        """
        Classify engagement quality as high, medium, or low.
        
        High: many comments, positive sentiment, multiple themes
        Medium: moderate engagement
        Low: few comments, one-sided sentiment
        """
        score = post.get("score", 0)
        comment_count = len(comments)
        upvote_ratio = 0.0
        
        if comments:
            total_up = sum(c.get("upvotes", 0) for c in comments)
            total_down = sum(c.get("downvotes", 0) for c in comments)
            total = total_up + total_down + 1
            upvote_ratio = total_up / total

        sentiment = self.sentiment_analysis(post, comments)
        sentiment_balance = abs(sentiment["positive"] - sentiment["negative"])

        # Scoring rubric
        quality_score = 0

        # Comment volume
        if comment_count >= 20:
            quality_score += 3
        elif comment_count >= 10:
            quality_score += 2
        elif comment_count >= 3:
            quality_score += 1

        # Upvote ratio (quality commenters)
        if upvote_ratio >= 0.8:
            quality_score += 2
        elif upvote_ratio >= 0.6:
            quality_score += 1

        # Score
        if score >= 500:
            quality_score += 2
        elif score >= 100:
            quality_score += 1

        # Sentiment diversity
        if sentiment_balance < 0.3 and comment_count > 5:
            quality_score -= 1  # echo chamber

        if quality_score >= 6:
            return "high"
        elif quality_score >= 3:
            return "medium"
        else:
            return "low"