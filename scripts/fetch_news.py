from supabase import create_client, Client
from gnews import GNews
import os
import time
import logging
from functools import wraps
from typing import Callable
from urllib.parse import quote

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Initialize GNews
google_news = GNews(
    language=os.getenv("GNEWS_LANGUAGE", "en"),
    country=os.getenv("GNEWS_COUNTRY", "NG"),
    period=os.getenv("GNEWS_PERIOD", "7d"),
    max_results=int(os.getenv("GNEWS_MAX_RESULTS", 10))
)

TOPICS = ['WORLD', 'NATION', 'BUSINESS', 'TECHNOLOGY', 'ENTERTAINMENT', 'SPORTS', 
          'SCIENCE', 'HEALTH', 'POLITICS', 'CELEBRITIES', 'ECONOMY', 'FINANCE',
          'EDUCATION', 'FOOD', 'TRAVEL']

COUNTRIES = {
    'Nigeria': 'NG',
    'United_States': 'US',
    'Canada': 'CA',
    'Russia': 'RU',
    'Israel': 'IL',
    'Germany': 'DE'
}

def retry_with_backoff(retries=3, backoff_in_seconds=1):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if x == retries:
                        raise e
                    wait = (backoff_in_seconds * 2 ** x)
                    logger.warning(f"Attempt {x + 1} failed. Retrying in {wait} seconds...")
                    time.sleep(wait)
                    x += 1
        return wrapper
    return decorator

def format_article(article, category="general"):
    url = article.get("url", "")
    base_url = url.split('?')[0]
    
    return {
        "title": article.get("title", "").strip(),
        "url": base_url,
        "published_date": article.get("published date", ""),
        "description": article.get("description", "").strip(),
        "image": article.get("image", ""),  # Add image URL
        "publisher": {
            "href": article.get("publisher", {}).get("href", "").strip(),
            "title": article.get("publisher", {}).get("title", "").strip()
        },
        "source": "gnews",
        "category": category,
        "created_at": time.strftime('%Y-%m-%d %H:%M:%S')
    }

@retry_with_backoff(retries=3)
def fetch_news(news_func, *args):
    return news_func(*args)

def main():
    try:
        all_articles = []
        processed_urls = set()
        
        # Get existing URLs from last 24 hours to avoid duplicates
        yesterday = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() - 86400))
        existing = supabase.table("articles")\
            .select("url")\
            .gte("created_at", yesterday)\
            .execute()
        
        # Add existing URLs to processed set
        for item in existing.data:
            processed_urls.add(item['url'])
        
        # Fetch country news
        for country_name, country_code in COUNTRIES.items():
            google_news.country = country_code
            safe_country_name = quote(country_name.replace('_', ' '))
            news = fetch_news(google_news.get_news_by_location, safe_country_name)
            if news:
                for article in news:
                    formatted = format_article(article, f"country_{country_code}")
                    if formatted['url'] not in processed_urls:
                        processed_urls.add(formatted['url'])
                        all_articles.append(formatted)

        # Fetch topic news
        for topic in TOPICS:
            news = fetch_news(google_news.get_news_by_topic, topic)
            if news:
                for article in news:
                    formatted = format_article(article, topic.lower())
                    if formatted['url'] not in processed_urls:
                        processed_urls.add(formatted['url'])
                        all_articles.append(formatted)

        if all_articles:
            # Use upsert with both URL and title to ensure no duplicates
            supabase.table("articles").upsert(
                all_articles,
                on_conflict="url"
            ).execute()

        logger.info(f"Successfully stored {len(all_articles)} unique articles")
        logger.info(f"Skipped {len(processed_urls) - len(all_articles)} duplicate articles")

    except Exception as e:
        logger.error(f"Failed to fetch and store news: {str(e)}")
        raise

if __name__ == "__main__":
    main()
