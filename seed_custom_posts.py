#!/usr/bin/env python3
"""
seed_custom_posts.py
Bulk-insert the 42 custom posts into MongoDB via the /custom-post endpoint.
"""

import json
import requests
from datetime import datetime
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ENDPOINT = "http://localhost:8000/custom-post"
PAYLOAD_FILE = "custom_posts_payload.json"

def load_posts() -> List[Dict]:
    with open(PAYLOAD_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def seed():
    posts = load_posts()
    logger.info(f"Loaded {len(posts)} posts from {PAYLOAD_FILE}")

    for post in posts:
        body = {
    "title": post["title"],
    "content": post["content"],
    "author": post["author"],
    "category": post["category"],
    "published_date": post["published_date"] or "",
    "image": "",            # send empty string instead of None
}
        try:
            r = requests.post(ENDPOINT, json=body, timeout=15)
            r.raise_for_status()
            logger.info(f"✅ {post['published_date']} | {post['title'][:50]}...")
        except requests.RequestException as e:
            logger.error(f"❌ Failed to insert '{post['title'][:50]}...': {e}")

if __name__ == "__main__":
    seed()