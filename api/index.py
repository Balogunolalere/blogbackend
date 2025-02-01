import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

@app.get("/api/cron")
async def cron_handler():
    """Endpoint for Vercel cron job"""
    from main import fetch_and_store_news, logger
    try:
        logger.info("Starting cron job for news fetch")
        await fetch_and_store_news()
        logger.info("Cron job completed successfully")
        return {"status": "success", "message": "Cron job completed successfully"}
    except Exception as e:
        logger.error(f"Cron job failed: {str(e)}")
        return {"status": "error", "message": str(e)}

handler = app