
from fastapi import FastAPI, HTTPException, Request, Query
from pymongo import MongoClient
from gnews import GNews
import json
import time
from functools import wraps
from typing import List, Dict, Callable
import logging
from urllib.parse import quote, unquote
from fastapi.responses import FileResponse
from PIL import Image, ImageDraw, ImageFont
import textwrap
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

# Initialize MongoDB client
mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
mongo_db_name = os.getenv("MONGODB_DB", "blogdb")
mongo_collection_name = os.getenv("MONGODB_COLLECTION", "articles")
mongo_client = MongoClient(mongo_uri)
db = mongo_client[mongo_db_name]
if mongo_collection_name not in db.list_collection_names():
    db.create_collection(mongo_collection_name)
articles_collection = db[mongo_collection_name]
# Ensure unique index on url for articles
articles_collection.create_index("url", unique=True)

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
    image: str = None  # Add image field
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
        "image": article.get("image", ""),  # Add image URL
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

@app.get("/news", response_model=List[Article])
async def get_news(category: str = None, limit: int = 10):
    """Get news articles with optional category filter"""
    try:
        query = {}
        if category:
            query["category"] = category
        articles = list(articles_collection.find(query).sort("published_date", -1).limit(limit))
        for article in articles:
            article.pop("_id", None)
        return articles
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/news", response_model=Article)
async def add_custom_news(article: Article):
    """Add custom news article"""
    try:
        data = article.dict()
        articles_collection.update_one({"url": data["url"]}, {"$set": data}, upsert=True)
        return data
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
        query = {}
        if search:
            query["$text"] = {"$search": search}
        if category:
            query["category"] = category
        per_page = 12
        offset = (page - 1) * per_page
        total_articles = articles_collection.count_documents(query)
        articles = list(articles_collection.find(query).sort("published_date", -1).skip(offset).limit(per_page))
        for article in articles:
            article.pop("_id", None)
        total_pages = (total_articles + per_page - 1) // per_page
        categories = TOPICS + [f"country_{code}" for code in COUNTRIES.values()]
        return templates.TemplateResponse("index.html", {
            "request": request,
            "articles": articles,
            "current_page": page,
            "total_pages": total_pages,
            "search": search,
            "category": category,
            "categories": categories,
        })
    except Exception as e:
        logger.error(f"Error in home_page: {str(e)}")
        return HTMLResponse(f"<h1>Error: {str(e)}</h1>", status_code=500)

@app.get("/article/{url:path}", response_class=HTMLResponse)
async def article_details(request: Request, url: str):
    """Render article details page with structured data"""
    try:
        decoded_url = unquote(url).replace('_', '/')
        article = articles_collection.find_one({"url": decoded_url})
        if not article:
            logger.error(f"Article not found. URL: {url}, Decoded: {decoded_url}")
            raise HTTPException(status_code=404, detail=f"Article not found. Please check the URL.")
        article.pop("_id", None)
        related = list(articles_collection.find({"category": article["category"], "url": {"$ne": decoded_url}}).limit(3))
        for rel in related:
            rel.pop("_id", None)
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
                "related": related,
                "structured_data": json.dumps(structured_data, ensure_ascii=False)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/share-image/{url:path}")
async def generate_share_image(url: str):
    """Generate social share image for article"""
    try:
        decoded_url = unquote(url).replace('_', '/')
        article = articles_collection.find_one({"url": decoded_url})
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        img = Image.new('RGB', (1200, 630), color='white')
        d = ImageDraw.Draw(img)
        font_title = ImageFont.load_default()
        wrapped_text = textwrap.fill(article["title"], width=30)
        d.text((100, 100), wrapped_text, font=font_title, fill='black')
        temp_path = f"temp_{url}.png"
        img.save(temp_path)
        return FileResponse(
            temp_path,
            media_type="image/png",
            filename=f"article-{url}.png"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
