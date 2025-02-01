import sys
import os
import json
import asyncio
from http.server import BaseHTTPRequestHandler

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import fetch_and_store_news, logger

def run_async(func):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(func())
    loop.close()
    return result

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            logger.info("Starting cron job for news fetch")
            run_async(fetch_and_store_news)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {"status": "success", "message": "Cron job completed successfully"}
            self.wfile.write(json.dumps(response).encode())
            logger.info("Cron job completed successfully")
            
        except Exception as e:
            logger.error(f"Cron job failed: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            error_response = {"status": "error", "message": str(e)}
            self.wfile.write(json.dumps(error_response).encode())
