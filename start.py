"""Prepare the local environment and launch the selected ledger."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description="Mở Sổ Mộc trên máy cá nhân.")
    parser.add_argument("--mode", choices=["demo", "personal"])
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if sys.version_info < (3, 9):
        parser.exit(1, "Cần Python từ 3.9. Khuyến nghị Python 3.12.\n")
    mode = args.mode
    if mode is None:
        print("Sổ Mộc\n  1. Xem sổ mẫu\n  2. Mở sổ cá nhân")
        while True:
            choice = input("Nhấn Enter để xem mẫu, hoặc nhập 2 để dùng sổ cá nhân: ").strip()
            if choice in ("", "1", "2"):
                mode = "personal" if choice == "2" else "demo"
                break
    env = ROOT / ".venv"
    python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        subprocess.run([sys.executable, "-m", "venv", str(env)], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check",
                    "--no-index", "--find-links", str(ROOT / "wheels"),
                    "-r", str(ROOT / "requirements.txt")], check=True)
    command = [str(python), str(ROOT / "run.py"), "--mode", mode]
    if not args.no_browser:
        command.append("--open")
    os.chdir(ROOT)
    os.execv(str(python), command)

if __name__ == "__main__":
    main()
