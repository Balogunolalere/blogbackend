from fastapi import APIRouter
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import fetch_and_store_news

router = APIRouter()

@router.get("/api/cron")
async def cron_handler():
    await fetch_and_store_news()
    return {"status": "success", "message": "News fetch completed"}
