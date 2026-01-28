# main.py
import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
)
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode

import db
from config import BOT_TOKEN, DATABASE_URL
from keyboards import (
    kb_start,
    kb_contact,
    kb_levels,
    kb_confirm,
    kb_edit_fields,
    kb_material_menu,
    kb_done_button,
    kb_tingladim,
)

# ======================
# STATES
# ======================
REG_NAME = "REG_NAME"
REG_XJ_ID = "REG_XJ_ID"
REG_JOIN_DATE = "REG_JOIN_DATE"
REG_PHONE = "REG_PHONE"
REG_LEVEL = "REG_LEVEL"
REG_CONFIRM = "REG_CONFIRM"

MATERIAL_MENU = "MATERIAL_MENU"
STAGE3_TUTORIAL = "STAGE3_TUTORIAL"

CONFIRM_TEXT = "Tushundim ✅"

# ======================
bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()


# ======================
# STARTUP / SHUTDOWN
# ======================
async def on_startup():
    await db.init(DATABASE_URL)
    print("✅ DB connected & schema ready")

async def on_shutdown():
    await db.close()
    print("🛑 DB closed")


# ======================
# /start
# ======================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id

    inviter_id = None
    if message.text and message.text.startswith("/start ref_"):
        ref_code = message.text.replace("/start ref_", "").strip()
        inviter_id = await db.get_user_id_by_ref_code(ref_code)

    await db.ensure_user(user_id, inviter_id)

    await message.answer(
        "🤖 <b>XJ rasmiy bot tizimiga xush kelibsiz!</b>\n\n"
        "Bu yerda siz ro‘yxatdan o‘tasiz va ishni bosqichma-bosqich boshlaysiz.\n\n"
        "Boshlash uchun tugmani bosing 👇",
        reply_markup=kb_start()
    )


@dp.callback_query(F.data == "start:begin")
async def start_begin(call: CallbackQuery):
    await call.answer()
    await db.set_state(call.from_user.id, REG_NAME)
    await call.message.answer("Ro‘yxatdan o‘tishni boshlaymiz ✅\n\nIsm-familiyangizni yozing.")


# ======================
# TEXT HANDLER
# ======================
@dp.message(F.text)
async def text_handler(message: Message):
    user_id = message.from_user.id
    state = await db.get_state(user_id)
    text = message.text.strip()

    # 1️⃣ Ism-familiya
    if state == REG_NAME:
        if len(text) < 3:
            return await message.answer("Iltimos, ism-familiyani to‘liqroq yozing.")
        await db.set_user_field(user_id, "full_name", text)
        await db.set_state(user_id, REG_XJ_ID)
        return await message.answer("Rahmat ✅\n\nEndi XJ ID ni kiriting (7 xonali).")

    # 2️⃣ XJ ID
    if state == REG_XJ_ID:
        if not (text.isdigit() and len(text) == 7):
            return await message.answer("XJ ID 7 xonali raqam bo‘lishi kerak.\nMasalan: 0123456")
        await db.set_user_field(user_id, "xj_id", text)
        await db.set_state(user_id, REG_JOIN_DATE)
        return await message.answer("Qabul qilindi ✅\n\nXJ ga qachon qo‘shilgansiz? (erkin yozing)")

    # 3️⃣ Qo‘shilgan vaqt
    if state == REG_JOIN_DATE:
        await db.set_user_field(user_id, "join_date_text", text)
        await db.set_state(user_id, REG_PHONE)
        return await message.answer(
            "Tushunarli ✅\n\nEndi telefon raqamingizni yuboring 👇",
            reply_markup=kb_contact()
        )

    # 6️⃣ Stage 3 exact confirm
    if state == STAGE3_TUTORIAL:
        if text == CONFIRM_TEXT:
            await db.set_stage3_confirm(user_id, text)
            await db.reset_stage3_attempts(user_id)
            await db.set_state(user_id, MATERIAL_MENU)
            progress = await db.get_stage2(user_id)
            return await message.answer(
                "Zo‘r! ✅\n\nEndi XJ bilan to‘liq tanishamiz.",
                reply_markup=kb_material_menu(progress)
            )
        else:
            attempts = await db.inc_stage3_attempt(user_id)
            if attempts >= 3:
                return await message.answer(
                    f"Iltimos, <b>aynan</b> shunday yozing:\n{CONFIRM_TEXT}"
                )
            return await message.answer(f"Noto‘g‘ri ❌ ({attempts}/3)\n\n{CONFIRM_TEXT} deb yozing.")


# ======================
# CONTACT HANDLER
# ======================
@dp.message(F.contact)
async def contact_handler(message: Message):
    user_id = message.from_user.id
    state = await db.get_state(user_id)

    if state == REG_PHONE:
        await db.set_user_field(user_id, "phone", message.contact.phone_number)
        await db.set_state(user_id, REG_LEVEL)
        return await message.answer(
            "Rahmat ✅\n\nDarajangizni tanlang:",
            reply_markup=kb_levels()
        )


# ======================
# REG LEVEL
# ======================
@dp.callback_query(F.data.startswith("reg:level:"))
async def reg_level(call: CallbackQuery):
    await call.answer()
    level = call.data.split(":")[2]
    user_id = call.from_user.id

    await db.set_user_field(user_id, "level", level)
    await db.set_state(user_id, REG_CONFIRM)

    profile = await db.get_user_profile(user_id)

    text = (
        "Ma’lumotlaringizni tekshiring:\n\n"
        f"👤 Ism: {profile['full_name']}\n"
        f"🆔 XJ ID: {profile['xj_id']}\n"
        f"📅 Qo‘shilgan vaqt: {profile['join_date_text']}\n"
        f"📞 Telefon: {profile['phone']}\n"
        f"⭐ Daraja: {profile['level']}\n\n"
        "Tasdiqlaysizmi?"
    )

    await call.message.answer(text, reply_markup=kb_confirm())


# ======================
# REG CONFIRM
# ======================
@dp.callback_query(F.data == "reg:confirm:yes")
async def reg_confirm_yes(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id

    await db.set_state(user_id, MATERIAL_MENU)
    progress = await db.get_stage2(user_id)

    await call.message.answer(
        "🎉 <b>Ro‘yxatdan muvaffaqiyatli o‘tdingiz!</b>\n\n"
        "Endi XJ bilan to‘liq tanishib chiqamiz.",
        reply_markup=kb_material_menu(progress)
    )


@dp.callback_query(F.data == "reg:confirm:edit")
async def reg_confirm_edit(call: CallbackQuery):
    await call.answer()
    await call.message.answer(
        "Qaysi ma’lumotni o‘zgartirasiz?",
        reply_markup=kb_edit_fields()
    )


# ======================
# STAGE 2 MATERIALS
# ======================
@dp.callback_query(F.data.startswith("m2:open:"))
async def stage2_open(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    item = call.data.split(":")[2]

    if item == "text":
        await call.message.answer(
            "📘 <b>XJ kompaniyasi haqida</b>\n\n(XJ haqida to‘liq matn shu yerda bo‘ladi)",
            reply_markup=kb_done_button("✅ O‘qidim", "m2:done:matn")
        )

    if item == "audio":
        await call.message.answer(
            "🎧 XJ haqida audio tushuntirish",
            reply_markup=kb_done_button("✅ Tingladim", "m2:done:audio")
        )

    if item == "video":
        await call.message.answer(
            "🎥 XJ kompaniyasi haqida video",
            reply_markup=kb_done_button("✅ Ko‘rdim", "m2:done:video")
        )

    if item == "links":
        await call.message.answer(
            "🔗 Foydali havolalar:\n— Rasmiy sayt\n— Telegram\n— Instagram",
            reply_markup=kb_done_button("✅ Ko‘rdim", "m2:done:links")
        )


@dp.callback_query(F.data.startswith("m2:done:"))
async def stage2_done(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    key = call.data.split(":")[2] + "_done"

    await db.mark_stage2(user_id, key)
    progress = await db.get_stage2(user_id)

    await call.message.answer(
        "Saqlandi ✅",
        reply_markup=kb_material_menu(progress)
    )

@dp.callback_query(F.data == "m2:locked")
async def m2_locked(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    p = await db.get_stage2(user_id)

    missing = []
    if not p.get("matn_done", False):  missing.append("📘 Matn")
    if not p.get("audio_done", False): missing.append("🎧 Audio")
    if not p.get("video_done", False): missing.append("🎥 Video")
    if not p.get("links_done", False): missing.append("🔗 Linklar")

    await call.message.answer("⛔ Davom etish yopiq.\nQolganlar:\n" + "\n".join(missing))
@dp.callback_query(F.data == "m2:continue")
async def stage2_continue(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id

    await db.set_state(user_id, STAGE3_TUTORIAL)
    await call.message.answer(
        "🎧 <b>Ishni boshlash uchun to‘liq darslik</b>\n\n"
        "Audio tugagach aynan shunday yozing:\n"
        f"<b>{CONFIRM_TEXT}</b>",
        reply_markup=kb_tingladim("noop")
    )


# ======================
# MAIN
# ======================
async def main():
    await on_startup()
    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
