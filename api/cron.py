from http.server import BaseHTTPRequestHandler
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import fetch_and_store_news
import asyncio

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        asyncio.run(fetch_and_store_news())
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('Cron job completed'.encode())
        return
