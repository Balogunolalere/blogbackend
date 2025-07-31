from pymongo import MongoClient, UpdateOne
from gnews import GNews
import os
import time
import logging
from functools import wraps
from typing import Callable
from urllib.parse import quote
from dotenv import load_dotenv


# Load environment variables strictly from .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Read connection info from .env only
mongo_uri = os.environ["MONGODB_URI"]
mongo_db_name = os.environ["MONGODB_DB"]
mongo_collection_name = os.environ["MONGODB_COLLECTION"]
mongo_client = MongoClient(mongo_uri)
db = mongo_client[mongo_db_name]
if mongo_collection_name not in db.list_collection_names():
    db.create_collection(mongo_collection_name)
articles_collection = db[mongo_collection_name]
# Ensure unique index on url for articles
articles_collection.create_index("url", unique=True)

# Initialize GNews
google_news = GNews(
    language=os.environ["GNEWS_LANGUAGE"],
    country=os.environ["GNEWS_COUNTRY"],
    period=os.environ["GNEWS_PERIOD"],
    max_results=int(os.environ["GNEWS_MAX_RESULTS"])
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
        "image": article.get("image", ""),
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
    print(f"Using database: {mongo_db_name}")
    print(f"Using collection: {mongo_collection_name}")
    try:
        all_articles = []
        processed_urls = set()

        # Get existing URLs from last 24 hours to avoid duplicates
        yesterday = time.time() - 86400
        existing = articles_collection.find({
            "created_at": {"$gte": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(yesterday))}
        }, {"url": 1})
        for item in existing:
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
            # Upsert articles by url
            operations = []
            for article in all_articles:
                operations.append(
                    UpdateOne({"url": article["url"]}, {"$set": article}, upsert=True)
                )
            result = articles_collection.bulk_write(operations)

        logger.info(f"Successfully stored {len(all_articles)} unique articles")
        logger.info(f"Skipped {len(processed_urls) - len(all_articles)} duplicate articles")

    except Exception as e:
        logger.error(f"Failed to fetch and store news: {str(e)}")
        raise

if __name__ == "__main__":
    main()
