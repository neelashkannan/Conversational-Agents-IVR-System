import http.server
import socketserver
import webbrowser

PORT = 8080

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving at http://localhost:{PORT}")
    webbrowser.open(f"http://localhost:{PORT}/index.html")
    httpd.serve_forever()

