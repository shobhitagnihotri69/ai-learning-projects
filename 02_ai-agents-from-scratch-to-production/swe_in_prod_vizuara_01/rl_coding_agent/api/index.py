from http.server import BaseHTTPRequestHandler
import sys
import os

# Add the parent directory to the Python path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our cleaned-up agent
from agent import main

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Respond with OK status
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        
        self.wfile.write("=== RL Coding Agent (Vercel Serverless) ===\n\n".encode('utf-8'))
        self.wfile.write("Starting GRPO training step. Check logs for timeout info.\n\n".encode('utf-8'))
        
        try:
            # Execute the RL Coding Agent
            result = main()
            self.wfile.write(f"\nCompleted successfully! Result: {result}\n".encode('utf-8'))
        except Exception as e:
            self.wfile.write(f"\nError encountered: {str(e)}\n".encode('utf-8'))
        return
