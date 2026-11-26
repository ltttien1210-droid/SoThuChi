"""Run the personal ledger by default, or pass --mode demo."""
import argparse
import os
from pathlib import Path
import webbrowser
import uvicorn

ROOT = Path(__file__).resolve().parent

def serve(mode="personal", open_browser=False):
    demo = mode == "demo"
    port = 8001 if demo else 8000
    url = f"http://127.0.0.1:{port}"
    os.environ["APP_ORIGIN"] = url
    os.environ["LEDGER_DEMO"] = "1" if demo else "0"
    if demo:
        os.environ["LEDGER_DB"] = str(ROOT / "data/demo.sqlite3")
        from demo import seed
        seed()
    else:
        os.environ.setdefault("LEDGER_DB", str(ROOT / "data/ledger.sqlite3"))

    class LocalServer(uvicorn.Server):
        async def startup(self, sockets=None):
            await super().startup(sockets=sockets)
            if self.started:
                print(f"Mở {url} · Dừng bằng Ctrl+C", flush=True)
                if open_browser:
                    webbrowser.open(url)

    LocalServer(uvicorn.Config("app.main:app", host="127.0.0.1", port=port, proxy_headers=False)).run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("personal", "demo"), default="personal")
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    serve(args.mode, args.open)
