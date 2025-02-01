import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, fetch_and_store_news
from fastapi import Request

@app.get("/api/cron")
async def cron_endpoint(request: Request):
    await fetch_and_store_news()
    return {"status": "success", "message": "Cron job completed"}

# This is required for Vercel deployment
handler = app