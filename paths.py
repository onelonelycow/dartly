"""
paths.py — where the app keeps its data files.

By default everything lives next to the code (great for running locally). On a
host like Render you can set the DATA_DIR environment variable to a mounted
persistent disk (e.g. /var/data) and the database, your profile, and alert
preferences will survive redeploys — no code changes needed.
"""
import os
from pathlib import Path

# DATA_DIR env var wins; otherwise use the folder this file sits in.
DATA_DIR = Path(os.environ.get("DATA_DIR") or Path(__file__).parent)
DATA_DIR.mkdir(parents=True, exist_ok=True)


def data_file(name: str) -> Path:
    """Absolute path to a data file (db, json, …) inside DATA_DIR."""
    return DATA_DIR / name
