# config.py
import os

def _must(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

BOT_TOKEN = _must("BOT_TOKEN")
DATABASE_URL = _must("DATABASE_URL")

# ADMIN_IDS="199169309"
ADMIN_IDS = set()
_admin_raw = os.getenv("ADMIN_IDS", "").strip()
if _admin_raw:
    for part in _admin_raw.split(","):
        part = part.strip()
        if part.isdigit():
            ADMIN_IDS.add(int(part))
  
