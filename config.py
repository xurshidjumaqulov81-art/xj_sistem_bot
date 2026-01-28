# config.py
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# keyingi bot linki (ixtiyoriy)
NEXT_BOT_LINK = os.getenv("NEXT_BOT_LINK", "").strip()

# Adminlar: "12345,67890"
_admins_raw = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS = []
if _admins_raw:
    ADMIN_IDS = [int(x.strip()) for x in _admins_raw.split(",") if x.strip().isdigit()]
