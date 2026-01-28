# main.py
import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile
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
    kb_stage3_tingladim,
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

STAGE3_AUDIO = "STAGE3_AUDIO"  # audio yuborilgan, "Тингладим" kutiladi
STAGE3_NOTE = "STAGE3_NOTE"    # izoh yozish kutiladi

# Keyingi bosqich (hozircha placeholder)
STAGE4_INTRO = "STAGE4_INTRO"

# Boshqa bot link (Railway Variables’da ham berib qo‘ysangiz bo‘ladi)
NEXT_BOT_LINK = os.getenv("NEXT_BOT_LINK", "https://t.me/OTHER_BOT_USERNAME")

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
    await db.ensure_user(user_id)

    await message.answer(
        "🤖 <b>ХЖ расмий бот тизимига хуш келибсиз!</b>\n\n"
        "Бу ерда сиз рўйхатдан ўтасиз ва ишни босқичма-босқич бошлайсиз.\n\n"
        "Бошлаш учун тугмани босинг 👇",
        reply_markup=kb_start()
    )


@dp.callback_query(F.data == "start:begin")
async def start_begin(call: CallbackQuery):
    await call.answer()
    await db.set_state(call.from_user.id, REG_NAME)
    await call.message.answer("Рўйхатдан ўтишни бошлаймиз ✅\n\nИсм-фамилиянгизни ёзинг.")


# ======================
# TEXT HANDLER
# ======================
@dp.message(F.text)
async def text_handler(message: Message):
    user_id = message.from_user.id
    state = await db.get_state(user_id)
    text = message.text.strip()

    # 1) Ism-familiya
    if state == REG_NAME:
        if len(text) < 3:
            return await message.answer("Илтимос, исм-фамилияни тўлиқроқ ёзинг.")
        await db.set_user_field(user_id, "full_name", text)
        await db.set_state(user_id, REG_XJ_ID)
        return await message.answer("Раҳмат ✅\n\nЭнди ХЖ ID ни киритинг (7 хонали).")

    # 2) XJ ID
    if state == REG_XJ_ID:
        if not (text.isdigit() and len(text) == 7):
            return await message.answer("ХЖ ID 7 хонали рақам бўлиши керак.\nМасалан: 0123456")
        await db.set_user_field(user_id, "xj_id", text)
        await db.set_state(user_id, REG_JOIN_DATE)
        return await message.answer("Қабул қилинди ✅\n\nХЖ га қачон қўшилгансиз? (эркин ёзинг)")

    # 3) Qo‘shilgan vaqt
    if state == REG_JOIN_DATE:
        await db.set_user_field(user_id, "join_date_text", text)
        await db.set_state(user_id, REG_PHONE)
        return await message.answer(
            "Тушунарли ✅\n\nЭнди телефон рақамингизни юборинг 👇",
            reply_markup=kb_contact()
        )

    # ======================
    # STAGE 3 NOTE (11 audio)
    # ======================
    if state == STAGE3_NOTE:
        if len(text) < 2:
            return await message.answer("Илтимос, камида 2та ҳарфдан иборат изоҳ ёзинг.")

        s3 = await db.get_stage3(user_id)
        lesson = int(s3["current_lesson"])

        # save note
        await db.save_stage3_note(user_id, lesson, text)

        next_lesson = lesson + 1

        if next_lesson <= 11:
            await db.set_stage3_lesson(user_id, next_lesson)
            await db.set_state(user_id, STAGE3_AUDIO)
            await message.answer("✅ Изоҳ сақланди. Кейинги аудио 👇")
            return await send_stage3_audio(message, lesson=next_lesson)

        # finish 11
        await db.complete_stage3(user_id)
        await db.set_state(user_id, STAGE4_INTRO)
        return await message.answer(
            "🎉 <b>Сиз тўлиқ дарсликни олдингиз!</b>\n\n"
            "Энди навбатдаги босқичга чиқасиз 👇\n"
            f"➡️ {NEXT_BOT_LINK}"
        )


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
            "Раҳмат ✅\n\nДаражангизни танланг:",
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
        "Маълумотларингизни текширинг:\n\n"
        f"👤 Исм: {profile.get('full_name')}\n"
        f"🆔 ХЖ ID: {profile.get('xj_id')}\n"
        f"📅 Қўшилган вақт: {profile.get('join_date_text')}\n"
        f"📞 Телефон: {profile.get('phone')}\n"
        f"⭐ Даража: {profile.get('level')}\n\n"
        "Тасдиқлайсизми?"
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

    # ✅ har registratsiyadan keyin stage2 reset
    await db.reset_stage2(user_id)

    progress = await db.get_stage2(user_id)

    await call.message.answer(
        "🎉 <b>Рўйхатдан муваффақиятли ўтдингиз!</b>\n\n"
        "Энди ХЖ билан тўлиқ танишиб чиқамиз.",
        reply_markup=kb_material_menu(progress)
    )


@dp.callback_query(F.data == "reg:confirm:edit")
async def reg_confirm_edit(call: CallbackQuery):
    await call.answer()
    await call.message.answer(
        "Қайси маълумотни ўзгартирсиз?",
        reply_markup=kb_edit_fields()
    )


@dp.callback_query(F.data.startswith("reg:edit:"))
async def reg_edit_field(call: CallbackQuery):
    await call.answer()
    field = call.data.split(":")[2]
    user_id = call.from_user.id

    if field == "full_name":
        await db.set_state(user_id, REG_NAME)
        return await call.message.answer("Исм-фамилиянгизни қайта ёзинг:")

    if field == "xj_id":
        await db.set_state(user_id, REG_XJ_ID)
        return await call.message.answer("ХЖ ID ни қайта киритинг (7 хонали):")

    if field == "join_date_text":
        await db.set_state(user_id, REG_JOIN_DATE)
        return await call.message.answer("ХЖ га қачон қўшилгансиз? (эркин ёзинг):")

    if field == "phone":
        await db.set_state(user_id, REG_PHONE)
        return await call.message.answer("Телефон рақамингизни қайта юборинг 👇", reply_markup=kb_contact())

    if field == "level":
        await db.set_state(user_id, REG_LEVEL)
        return await call.message.answer("Даражангизни қайта танланг:", reply_markup=kb_levels())


# ======================
# STAGE 2 MATERIALS
# ======================
@dp.callback_query(F.data.startswith("m2:open:"))
async def stage2_open(call: CallbackQuery):
    await call.answer()
    item = call.data.split(":")[2]

    if item == "text":
        return await call.message.answer(
            "📘 <b>ХЖ компанияси ҳақида</b>\n\n(ХЖ ҳақида тўлиқ матн шу ерда бўлади)",
            reply_markup=kb_done_button("✅ Ўқидим", "m2:done:matn")
        )

    if item == "audio":
        return await call.message.answer(
            "🎧 ХЖ ҳақида аудио тушунтириш\n\n(Ҳозирча аудио ўрнига матн турибди. Кейин аудио қўшасиз.)",
            reply_markup=kb_done_button("✅ Тингладим", "m2:done:audio")
        )

    if item == "video":
        return await call.message.answer(
            "🎥 ХЖ компанияси ҳақида видео\n\n(Ҳозирча видео ўрнига матн турибди. Кейин видео/линк қўшасиз.)",
            reply_markup=kb_done_button("✅ Кўрдим", "m2:done:video")
        )

    if item == "links":
        return await call.message.answer(
            "🔗 Фойдали ҳаволалар:\n— Расмий сайт\n— Телеграм\n— Инстаграм",
            reply_markup=kb_done_button("✅ Кўрдим", "m2:done:links")
        )


@dp.callback_query(F.data.startswith("m2:done:"))
async def stage2_done(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    key = call.data.split(":")[2] + "_done"

    await db.mark_stage2(user_id, key)
    progress = await db.get_stage2(user_id)

    all_done = (
        progress.get("matn_done", False)
        and progress.get("audio_done", False)
        and progress.get("video_done", False)
        and progress.get("links_done", False)
    )

    if all_done:
        txt = "🎉 Ҳаммаси тайёр! Энди ➡️ Давом этиш ни босинг."
    else:
        txt = "Сақланди ✅"

    await call.message.answer(txt, reply_markup=kb_material_menu(progress))


@dp.callback_query(F.data == "m2:locked")
async def m2_locked(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    p = await db.get_stage2(user_id)

    missing = []
    if not p.get("matn_done", False):  missing.append("📘 Матн")
    if not p.get("audio_done", False): missing.append("🎧 Аудио")
    if not p.get("video_done", False): missing.append("🎥 Видео")
    if not p.get("links_done", False): missing.append("🔗 Линклар")

    if not missing:
        return await call.message.answer("Ҳаммаси тайёр ✅ Энди ➡️ Давом этиш ни босинг.")

    await call.message.answer("⛔ Давом этиш ёпиқ.\nҚолганлар:\n" + "\n".join(missing))


@dp.callback_query(F.data == "m2:continue")
async def stage2_continue(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    progress = await db.get_stage2(user_id)

    all_done = (
        progress.get("matn_done", False)
        and progress.get("audio_done", False)
        and progress.get("video_done", False)
        and progress.get("links_done", False)
    )

    if not all_done:
        return await call.message.answer("⛔ Аввал 4 та материални ҳам бажаринг.")

    # ✅ start Stage3 (11 audio + notes)
    await db.reset_stage3(user_id)
    await db.set_state(user_id, STAGE3_AUDIO)
    await send_stage3_audio(call.message, lesson=1)


# ======================
# STAGE 3 (11 AUDIO)
# ======================
async def send_stage3_audio(message: Message, lesson: int):
    filename = f"content/stage3/{lesson:02d}.mp3"
    audio = FSInputFile(filename)

    await message.answer(
        f"🎧 <b>Ишни бошлаш учун тўлиқ дарслик</b>\n\n"
        f"{lesson}/11 — Аудиони тингланг 👇"
    )
    await message.answer_audio(audio)
    await message.answer(
        "Аудио тугагач, пастдаги тугмани босинг:",
        reply_markup=kb_stage3_tingladim()
    )


@dp.callback_query(F.data == "s3:ready_note")
async def s3_ready_note(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id

    state = await db.get_state(user_id)
    if state != STAGE3_AUDIO:
        return await call.message.answer("Бу тугма ҳозир актив эмас.")

    s3 = await db.get_stage3(user_id)
    lesson = int(s3["current_lesson"])

    await db.set_state(user_id, STAGE3_NOTE)
    await call.message.answer(
        f"✍️ <b>{lesson}-аудиодан</b> нимани тушундингиз?\n"
        "Қисқа изоҳ ёзинг (1-2 жумла ҳам бўлади)."
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
