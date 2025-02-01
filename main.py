from fastapi import FastAPI, HTTPException, Request, Query
from supabase import create_client, Client
from gnews import GNews
import json
import time
from functools import wraps
from typing import Callable, List, Dict
import logging
from urllib.parse import quote, unquote
import asyncio

import os
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

# Load environment variables
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Initialize FastAPI
app = FastAPI(title="Blog API")

# Initialize templates and static files
templates = Jinja2Templates(directory="templates")

# Pydantic models
class Article(BaseModel):
    title: str
    url: str
    published_date: str
    description: str
    publisher: Dict[str, str]
    source: str = "gnews"
    category: str = "general"

# Your existing utility functions
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

@retry_with_backoff(retries=3)
def fetch_news(news_func, *args):
    """Wrapper function to handle retries for news fetching"""
    return news_func(*args)

def format_article(article, category="general"):
    """Format article and clean the URL to ensure consistency"""
    # Clean the URL by removing tracking parameters
    url = article.get("url", "")
    base_url = url.split('?')[0]  # Remove query parameters
    
    formatted = {
        "title": article.get("title", "").strip(),
        "url": base_url,  # Use cleaned URL
        "published_date": article.get("published date", ""),
        "description": article.get("description", "").strip(),
        "publisher": {
            "href": article.get("publisher", {}).get("href", "").strip(),
            "title": article.get("publisher", {}).get("title", "").strip()
        },
        "source": "gnews",
        "category": category
    }
    return formatted

# Initialize GNews with environment variables
google_news = GNews(
    language=os.getenv("GNEWS_LANGUAGE", "en"),
    country=os.getenv("GNEWS_COUNTRY", "NG"),
    period=os.getenv("GNEWS_PERIOD", "7d"),
    max_results=int(os.getenv("GNEWS_MAX_RESULTS", 10))
)

# Your existing TOPICS and COUNTRIES definitions
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

async def fetch_and_store_news():
    """Fetch news and store in Supabase with duplicate handling"""
    try:
        all_articles = []
        processed_urls = set()  # Track URLs we've seen
        
        # Fetch country news
        for country_name, country_code in COUNTRIES.items():
            google_news.country = country_code
            safe_country_name = quote(country_name.replace('_', ' '))
            news = fetch_news(google_news.get_news_by_location, safe_country_name)
            if news:
                for article in news:
                    formatted = format_article(article, f"country_{country_code}")
                    # Only add if we haven't seen this URL
                    if formatted['url'] not in processed_urls:
                        processed_urls.add(formatted['url'])
                        all_articles.append(formatted)

        # Fetch topic news
        for topic in TOPICS:
            news = fetch_news(google_news.get_news_by_topic, topic)
            if news:
                for article in news:
                    formatted = format_article(article, topic.lower())
                    # Only add if we haven't seen this URL
                    if formatted['url'] not in processed_urls:
                        processed_urls.add(formatted['url'])
                        all_articles.append(formatted)

        # Use upsert to handle duplicates in database
        if all_articles:
            supabase.table("articles").upsert(
                all_articles,
                on_conflict="url"  # Use URL as the conflict resolution key
            ).execute()

        logger.info(f"Successfully stored {len(all_articles)} unique articles")
        return all_articles

    except Exception as e:
        logger.error(f"Failed to fetch and store news: {str(e)}")
        raise

from datetime import datetime, timedelta, time as datetime_time

async def schedule_news_fetch():
    """Schedule news fetching to run at 1 AM daily"""
    while True:
        # Calculate time until next 1 AM
        now = datetime.now()
        target_time = datetime_time(hour=1, minute=0)  # 1:00 AM
        
        # Calculate next run time
        next_run = datetime.combine(now.date(), target_time)
        if now.time() >= target_time:
            next_run += timedelta(days=1)  # If it's past 1 AM, schedule for tomorrow
        
        # Calculate seconds until next run
        delay = (next_run - now).total_seconds()
        
        # Sleep until next scheduled time
        logger.info(f"Next news fetch scheduled for: {next_run}")
        await asyncio.sleep(delay)
        
        # Fetch news
        await fetch_and_store_news()

@app.on_event("startup")
async def startup_event():
    """Start the news fetching schedule on startup"""
    asyncio.create_task(schedule_news_fetch())

@app.get("/news", response_model=List[Article])
async def get_news(category: str = None, limit: int = 10):
    """Get news articles with optional category filter"""
    try:
        query = supabase.table("articles").select("*")
        if category:
            query = query.eq("category", category)
        result = query.limit(limit).order("published_date", desc=True).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/news", response_model=Article)
async def add_custom_news(article: Article):
    """Add custom news article"""
    try:
        result = supabase.table("articles").insert(article.dict()).execute()
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def home_page(
    request: Request, 
    page: int = Query(1, ge=1),
    search: str = Query(None),
    category: str = Query(None)
):
    """Render homepage with news articles, pagination and search"""
    try:
        # Initialize query
        query = supabase.table("articles").select("*", count="exact")
        
        # Apply filters
        if search:
            query = query.ilike("title", f"%{search}%")
        if category:
            query = query.eq("category", category)
        
        # Calculate pagination
        per_page = 12
        offset = (page - 1) * per_page
        
        # Execute query with pagination
        result = query.order("published_date", desc=True)\
            .range(offset, offset + per_page - 1)\
            .execute()
        
        total_articles = result.count
        total_pages = (total_articles + per_page - 1) // per_page

        return templates.TemplateResponse(
            "index.html", 
            {
                "request": request,
                "articles": result.data,
                "current_page": page,
                "total_pages": total_pages,
                "search": search,
                "category": category,
                "categories": TOPICS,
            }
        )
    except Exception as e:
        logger.error(f"Error in home_page: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/article/{url:path}", response_class=HTMLResponse)
async def article_details(request: Request, url: str):
    """Render article details page with structured data"""
    try:
        # Decode URL and convert back from our safe format
        decoded_url = unquote(url).replace('_', '/')
        
        # Get article from database
        result = supabase.table("articles")\
            .select("*")\
            .eq("url", decoded_url)\
            .execute()
            
        if not result.data:
            logger.error(f"Article not found. URL: {url}, Decoded: {decoded_url}")
            raise HTTPException(
                status_code=404, 
                detail=f"Article not found. Please check the URL."
            )
        
        article = result.data[0]
        # Get related articles from same category
        related = supabase.table("articles")\
            .select("*")\
            .eq("category", article["category"])\
            .neq("url", url)\
            .limit(3)\
            .execute()
        
        # Create structured data for article
        structured_data = {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": article["title"],
            "description": article["description"],
            "datePublished": article["published_date"],
            "url": article["url"],
            "publisher": {
                "@type": "Organization",
                "name": article["publisher"]["title"],
                "url": article["publisher"]["href"]
            },
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": str(request.url)
            },
            "articleSection": article["category"]
        }

        return templates.TemplateResponse(
            "article.html", 
            {
                "request": request, 
                "article": article,
                "related": related.data,
                "structured_data": json.dumps(structured_data, ensure_ascii=False)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cron")
async def cron_job():
    """Endpoint for Vercel cron job to trigger news fetching"""
    try:
        await fetch_and_store_news()
        return {"status": "success", "message": "News fetched and stored successfully"}
    except Exception as e:
        logger.error(f"Cron job failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
