"""No-cache HTTP server for JupyterLite development."""

import http.server
import os
import sys

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
outdir = sys.argv[2] if len(sys.argv) > 2 else "../build/html"

os.chdir(outdir)


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass  # silence request noise


print(f"Serving {outdir} on http://localhost:{port}/")
http.server.HTTPServer(("", port), NoCacheHandler).serve_forever()
