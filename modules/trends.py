"""Hacker News + Reddit 트렌드 수집"""
import json
import logging
import requests
from datetime import datetime
from config import Config

log = logging.getLogger("shorts.trends")

HN_TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

REDDIT_SUBREDDITS = [
    "devops", "MachineLearning", "kubernetes",
    "LocalLLaMA", "programming", "aws",
]

TECH_KEYWORDS = [
    "ai", "llm", "kubernetes", "docker", "devops", "claude", "gemini", "gpt",
    "openai", "anthropic", "ml", "gpu", "serverless", "cicd", "terraform",
    "python", "rust", "go", "kafka", "redis", "postgres", "k8s", "helm",
    "agent", "rag", "vector", "embedding", "fine-tune", "open source", "github",
]

HOT_KEYWORDS = [
    "new", "introduce", "release", "launch", "faster", "better",
    "free", "open source", "vs", "outperform", "beats",
]


def fetch_hn_stories(limit: int = 30) -> list[dict]:
    """Hacker News 상위 스토리 수집"""
    log.info("Hacker News 수집 중...")
    try:
        ids = requests.get(HN_TOP_URL, timeout=10).json()[:100]
    except Exception as e:
        log.warning("HN 목록 가져오기 실패: %s", e)
        return []

    stories = []
    for story_id in ids[:50]:
        try:
            item = requests.get(HN_ITEM_URL.format(story_id), timeout=5).json()
        except Exception:
            continue
        if not item or item.get("type") != "story":
            continue
        title = (item.get("title") or "").lower()
        if any(kw in title for kw in TECH_KEYWORDS):
            stories.append({
                "source": "hackernews",
                "title": item.get("title"),
                "url": item.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                "score": item.get("score", 0),
                "comments": item.get("descendants", 0),
                "time": datetime.fromtimestamp(item.get("time", 0)).isoformat(),
            })
        if len(stories) >= limit:
            break
    log.info("HN: %d개 수집 완료", len(stories))
    return stories


def fetch_reddit_posts(limit_per_sub: int = 10) -> list[dict]:
    """Reddit 트렌드 수집 (인증 없이 JSON API)"""
    log.info("Reddit 수집 중...")
    headers = {"User-Agent": "infograb-shorts-bot/1.0"}
    posts = []
    for sub in REDDIT_SUBREDDITS:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit_per_sub}"
            data = requests.get(url, headers=headers, timeout=10).json()
            for post in data["data"]["children"]:
                p = post["data"]
                if p.get("stickied"):
                    continue
                posts.append({
                    "source": f"reddit/r/{sub}",
                    "title": p.get("title"),
                    "url": f"https://reddit.com{p.get('permalink')}",
                    "score": p.get("score", 0),
                    "comments": p.get("num_comments", 0),
                    "time": datetime.fromtimestamp(p.get("created_utc", 0)).isoformat(),
                })
        except Exception as e:
            log.warning("r/%s 실패: %s", sub, e)
    log.info("Reddit: %d개 수집 완료", len(posts))
    return posts


def _score_topic(item: dict) -> float:
    """숏츠 적합도 점수"""
    score = item.get("score", 0) * 0.5 + item.get("comments", 0) * 2
    title_lower = (item.get("title") or "").lower()
    for kw in HOT_KEYWORDS:
        if kw in title_lower:
            score += 500
    return score


def collect_trends(top_n: int = 10) -> dict:
    """트렌드 수집 → 점수 정렬 → 상위 N개 반환"""
    hn = fetch_hn_stories()
    reddit = fetch_reddit_posts()
    all_items = hn + reddit

    ranked = sorted(all_items, key=_score_topic, reverse=True)
    top = ranked[:top_n]

    result = {
        "fetched_at": datetime.now().isoformat(),
        "total_collected": len(all_items),
        "top_topics": top,
    }

    log.info("총 %d개 수집, 상위 %d개 선정", len(all_items), len(top))
    return result
