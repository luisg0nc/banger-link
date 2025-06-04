"""Health check endpoint for the Banger Link bot."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import logging

logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    """Simple HTTP server handler for health checks."""
    
    def do_GET(self):
        """Handle GET requests to the health check endpoint."""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_response(404)
            self.end_headers()

def run_health_check(port=8080):
    """Run the health check HTTP server in a separate thread."""
    def run():
        server_address = ('', port)
        httpd = HTTPServer(server_address, HealthHandler)
        logger.info(f"Health check server running on port {port}")
        httpd.serve_forever()
    
    # Start the health check server in a daemon thread
    health_thread = threading.Thread(target=run, daemon=True)
    health_thread.start()
    return health_thread
