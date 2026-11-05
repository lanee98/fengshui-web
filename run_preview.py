"""Run this upgraded copy without interrupting the user's existing service."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "webapp"))
from app import app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5002")), debug=False, use_reloader=False)
