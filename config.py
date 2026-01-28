# config.py
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

print("CONFIG LOADED")
print("BOT_TOKEN exists:", bool(BOT_TOKEN))
print("DATABASE_URL exists:", bool(DATABASE_URL))
