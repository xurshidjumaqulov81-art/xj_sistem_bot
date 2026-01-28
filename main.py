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
# Foydalanuvchi holatini vaqtincha saqlash (oddiy variant)
user_states = {}

@dp.message(F.text.lower() == "start")
async def start_reg(m: Message):
    user_states[m.from_user.id] = "waiting_fullname"
    await m.answer(
        "Ro‘yxatdan o‘tishni boshlaymiz ✅\n\n"
        "Iltimos, ism-familiyangizni yozing."
    )

@dp.message()
async def handle_steps(m: Message):
    user_id = m.from_user.id
    state = user_states.get(user_id)

    if state == "waiting_fullname":
        full_name = m.text.strip()
        user_states[user_id] = "registered"
        await m.answer(
            f"Rahmat, {full_name} ✅\n\n"
            "Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz.\n"
            "Keyingi bosqichni boshlaymiz."
        )
