# config.py
import os

# =========================
# TELEGRAM BOT TOKEN
# =========================
BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    "BU_YERGA_BOT_TOKEN_YOZISHINGIZ_MUMKIN"
)

# =========================
# DATABASE (Postgres)
# =========================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@host:port/dbname"
)

# =========================
# NEXT BOT / NEXT STEP
# =========================
# Agar keyingi bot yoki link bo‘lmasa — bo‘sh qoldiring
NEXT_BOT_LINK = os.getenv(
    "NEXT_BOT_LINK",
    ""
)

# =========================
# PROJECT SETTINGS
# =========================
PROJECT_NAME = "XJ SISTEM"
LANGUAGE = "uz_krill"

# =========================
# STAGE 3 SETTINGS
# =========================
STAGE3_TOTAL_AUDIOS = 11
