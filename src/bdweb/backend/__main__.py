"""
python -m bdweb

Starts the FastAPI backend and opens the browser.
In dev: run this alongside `npm run dev` in frontend/.
In prod: run this after `npm run build` in frontend/.
"""

import subprocess
import sys
import webbrowser
import time

import uvicorn


def main():
    port = 8000
    url = f"http://localhost:{port}"

    # Open browser after a short delay so the server is ready
    def _open():
        time.sleep(1.2)
        webbrowser.open(url)

    import threading
    threading.Thread(target=_open, daemon=True).start()

    print(f"bdweb running at {url}")
    uvicorn.run("bdweb.backend.server:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
