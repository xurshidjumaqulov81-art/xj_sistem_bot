import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

BOT_TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()

@dp.message(F.text == "/start")
async def start(m: Message):
    await m.answer(
        "XJ rasmiy bot tizimiga xush kelibsiz! 👋\n\n"
        "Boshlash uchun 'Start' deb yozing."
    )

@dp.message(F.text.lower() == "start")
async def go(m: Message):
    await m.answer("Zo‘r ✅ Bot ishlayapti. Endi bosqichlarni qo‘shamiz.")

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi. Railway Variables ga qo‘ying.")
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
