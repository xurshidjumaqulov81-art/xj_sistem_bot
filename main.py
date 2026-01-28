import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

BOT_TOKEN = os.getenv("BOT_TOKEN")
dp = Dispatcher()

# vaqtinchalik state
user_states = {}

@dp.message(F.text == "/start")
async def cmd_start(m: Message):
    await m.answer(
        "XJ rasmiy bot tizimiga xush kelibsiz! 👋\n\n"
        "Ro‘yxatdan o‘tishni boshlash uchun 'Start' deb yozing."
    )

# Start bosilganda registratsiya boshlansin (bitta handler!)
@dp.message(F.text.lower() == "start")
async def start_reg(m: Message):
    user_states[m.from_user.id] = "waiting_fullname"
    await m.answer(
        "Ro‘yxatdan o‘tishni boshlaymiz ✅\n\n"
        "Iltimos, ism-familiyangizni yozing."
    )

# Keyingi xabarlarni ushlab olamiz
@dp.message(F.text)
async def handle_steps(m: Message):
    user_id = m.from_user.id
    state = user_states.get(user_id)

    if state == "waiting_fullname":
        full_name = m.text.strip()
        if len(full_name) < 3:
            await m.answer("Iltimos, ism-familiyangizni to‘liq yozing 🙂")
            return

        user_states[user_id] = "registered"
        await m.answer(
            f"Rahmat, {full_name} ✅\n\n"
            "Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz.\n"
            "Keyingi bosqichni boshlaymiz."
        )
        return

    # agar state yo‘q bo‘lsa
    await m.answer("Boshlash uchun /start bosing, keyin 'Start' deb yozing.")

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi. Railway Variables ga qo‘ying.")
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
