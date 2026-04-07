#!/usr/bin/env python3
"""
Engagement Report Example
Generate and display a weekly engagement report for collected MoltBook data.
"""
import sys
sys.path.insert(0, "..")

from agent import MoltBookCollectionAgent

def main():
    print("=" * 60)
    print(" MoltBook Engagement Report")
    print("=" * 60)
    print()

    agent = MoltBookCollectionAgent()
    report = agent.generate_engagement_report()

    if "error" in report:
        print(f"Error: {report['error']}")
        sys.exit(1)

    print(f"Report period : {report['period']}")
    print(f"Generated at  : {report['report_date']}")
    print()
    print(f"📊 Posts collected  : {report['total_posts']}")
    print(f"💬 Total comments  : {report['total_comments']}")
    print(f"⬆️  Total upvotes   : {report['total_upvotes']}")
    print(f"📈 Total score     : {report['total_score']}")
    print(f"📉 Avg score/post   : {report['avg_score_per_post']}")
    print(f"💬 Avg comments/post: {report['avg_comments_per_post']}")
    print()

    quality = report["engagement_quality"]
    print(f"Engagement Quality:")
    print(f"  🟢 High   : {quality.get('high', 0)} posts")
    print(f"  🟡 Medium: {quality.get('medium', 0)} posts")
    print(f"  🔴 Low   : {quality.get('low', 0)} posts")
    print()

    sent = report["avg_sentiment"]
    print(f"Sentiment Breakdown:")
    print(f"  😊 Positive: {sent['positive']:.1%}")
    print(f"  😐 Neutral : {sent['neutral']:.1%}")
    print(f"  😞 Negative: {sent['negative']:.1%}")
    print()

    print("Top Themes:")
    for item in report["top_themes"]:
        bar = "█" * min(item["count"], 20)
        print(f"  #{item['theme']:<15} {bar} ({item['count']})")

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()