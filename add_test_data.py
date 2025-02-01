from dotenv import load_dotenv
import os
from supabase import create_client
from datetime import datetime, timedelta
import random

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Sample data
test_articles = [
    {
        "title": "Test Article: AI Revolution in 2024",
        "url": "https://example.com/ai-revolution-2024",
        "published_date": (datetime.now() - timedelta(days=1)).isoformat(),
        "description": "A comprehensive look at AI advancements expected in 2024.",
        "publisher": {
            "href": "https://example.com",
            "title": "Tech News Daily"
        },
        "source": "custom",
        "category": "technology"
    },
    {
        "title": "Sports Update: World Cup 2026 Preparations",
        "url": "https://example.com/world-cup-2026",
        "published_date": (datetime.now() - timedelta(days=2)).isoformat(),
        "description": "Countries begin preparations for the 2026 World Cup.",
        "publisher": {
            "href": "https://example.com",
            "title": "Sports Weekly"
        },
        "source": "custom",
        "category": "sports"
    },
    {
        "title": "Economic Forecast 2024",
        "url": "https://example.com/economy-2024",
        "published_date": (datetime.now() - timedelta(days=3)).isoformat(),
        "description": "Expert analysis of economic trends for 2024.",
        "publisher": {
            "href": "https://example.com",
            "title": "Finance Today"
        },
        "source": "custom",
        "category": "business"
    }
]

def add_test_data():
    """Add test articles to the database"""
    try:
        for article in test_articles:
            # Add some random variation to avoid exact duplicates
            article["title"] = f"{article['title']} {random.randint(1, 1000)}"
            article["url"] = f"{article['url']}-{random.randint(1, 1000)}"
            
            result = supabase.table("articles").insert(article).execute()
            print(f"Added article: {article['title']}")
        
        print("\nTest data added successfully!")
    except Exception as e:
        print(f"Error adding test data: {str(e)}")

if __name__ == "__main__":
    add_test_data()
