# config.py
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL missing")
