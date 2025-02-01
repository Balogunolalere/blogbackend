from http.server import BaseHTTPRequestHandler
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import fetch_and_store_news
import asyncio

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Vercel will make a GET request to /api/cron at 1 AM daily
        asyncio.run(fetch_and_store_news())  # Run the news fetching function
        self.send_response(200)  # Send success response
        return
