# main.py
import asyncio
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode

import db
from config import BOT_TOKEN, DATABASE_URL, NEXT_BOT_LINK
from keyboards import (
    kb_start,
    kb_contact,
    kb_levels,
    kb_confirm,
    kb_edit_fields,
    kb_material_menu,
    kb_done_button,
    kb_stage3_start,
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

STAGE3_INTRO = "STAGE3_INTRO"
STAGE3_WAIT_COMMENT = "STAGE3_WAIT_COMMENT"
DONE = "DONE"

# ======================
# FILE PATHS
# ======================
BASE_DIR = Path(__file__).resolve().parent
STAGE3_DIR = BASE_DIR / "content" / "stage3"

# IMPORTANT: names must match GitHub EXACTLY
STAGE3_AUDIO_FILES = [
    "10-ASOS DARSLIGI.mp3",
    "1-ASOS.mp3",
    "2-ASOS-COVER.mp3",
    "3-ASOS-COVER.mp3",
    "4-ASOS.mp3",
    "5-ASOS.mp3",
    "6-ASOS.mp3",
    "7-ASOS.mp3",
    "8-ASOS.mp3",
    "9-ASOS.mp3",
    "10-ASOS-2.mp3",
]

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

    # 1) full name
    if state == REG_NAME:
        if len(text) < 3:
            return await message.answer("Илтимос, исм-фамилияни тўлиқроқ ёзинг.")
        await db.set_user_field(user_id, "full_name", text)
        await db.set_state(user_id, REG_XJ_ID)
        return await message.answer("Раҳмат ✅\n\nЭнди <b>XJ ID</b> ни киритинг (7 хонали).")

    # 2) XJ ID
    if state == REG_XJ_ID:
        if not (text.isdigit() and len(text) == 7):
            return await message.answer("XJ ID 7 хонали рақам бўлиши керак.\nМасалан: 0123456")
        await db.set_user_field(user_id, "xj_id", text)
        await db.set_state(user_id, REG_JOIN_DATE)
        return await message.answer("Қабул қилинди ✅\n\nХЖ га қачон қўшилгансиз? (эркин ёзинг)")

    # 3) join date
    if state == REG_JOIN_DATE:
        await db.set_user_field(user_id, "join_date_text", text)
        await db.set_state(user_id, REG_PHONE)
        return await message.answer(
            "Тушунарли ✅\n\nЭнди телефон рақамингизни юборинг 👇",
            reply_markup=kb_contact()
        )

    # Stage3: waiting comment
    if state == STAGE3_WAIT_COMMENT:
        flow = await db.get_stage3_flow(user_id)
        idx = flow["current_idx"]

        # Save comment for current idx (1-based for humans)
        comment = text
        await db.save_stage3_comment(user_id, idx, comment)

        # Move next
        next_idx = idx + 1
        if next_idx >= len(STAGE3_AUDIO_FILES):
            await db.set_stage3_completed(user_id, True)
            await db.set_stage3_waiting(user_id, False)
            await db.set_state(user_id, DONE)

            return await message.answer(
                "✅ <b>Сиз тўлиқ дарсликни олдингиз!</b>\n\n"
                "Энди навбатдаги босқичга ўтасиз 👇\n"
                f"{NEXT_BOT_LINK}"
            )

        await db.set_stage3_idx(user_id, next_idx)
        return await send_stage3_audio(message, user_id, next_idx)

    # default
    return


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
        "Маʼлумотларингизни текширинг:\n\n"
        f"👤 Исм: {profile.get('full_name')}\n"
        f"🆔 XJ ID: {profile.get('xj_id')}\n"
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
        "Қайси маълумотни ўзгартирасиз?",
        reply_markup=kb_edit_fields()
    )


@dp.callback_query(F.data.startswith("edit:"))
async def edit_field(call: CallbackQuery):
    await call.answer()
    field = call.data.split(":")[1]
    user_id = call.from_user.id

    # route to state
    mapping = {
        "full_name": REG_NAME,
        "xj_id": REG_XJ_ID,
        "join_date_text": REG_JOIN_DATE,
        "phone": REG_PHONE,
        "level": REG_LEVEL,
    }
    new_state = mapping.get(field)
    if not new_state:
        return await call.message.answer("❌ Номаʼлум майдон.")

    await db.set_state(user_id, new_state)

    prompts = {
        REG_NAME: "Исм-фамилиянгизни қайта ёзинг:",
        REG_XJ_ID: "XJ ID ни қайта киритинг (7 хонали):",
        REG_JOIN_DATE: "ХЖ га қачон қўшилгансиз? (эркин ёзинг)",
        REG_PHONE: "Телефон рақамингизни қайта юборинг 👇",
        REG_LEVEL: "Даражангизни қайта танланг:",
    }

    if new_state == REG_PHONE:
        return await call.message.answer(prompts[new_state], reply_markup=kb_contact())
    if new_state == REG_LEVEL:
        return await call.message.answer(prompts[new_state], reply_markup=kb_levels())

    return await call.message.answer(prompts[new_state])


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
            "📘 <b>ХЖ компанияси ҳақида</b>\n\n(ХЖ ҳақида тўлиқ матн шу ерда бўлади)",
            reply_markup=kb_done_button("✅ Ўқидим", "m2:done:matn")
        )

    elif item == "audio":
        await call.message.answer(
            "🎧 ХЖ ҳақида аудио тушунтириш\n\n(Аудио шу ерга қўйилади ёки файл/линк)",
            reply_markup=kb_done_button("✅ Тингладим", "m2:done:audio")
        )

    elif item == "video":
        await call.message.answer(
            "🎥 ХЖ компанияси ҳақида видео\n\n(Видео шу ерга қўйилади ёки линк)",
            reply_markup=kb_done_button("✅ Кўрдим", "m2:done:video")
        )

    elif item == "links":
        await call.message.answer(
            "🔗 Фойдали ҳаволалар:\n— Расмий сайт\n— Telegram\n— Instagram",
            reply_markup=kb_done_button("✅ Кўрдим", "m2:done:links")
        )


@dp.callback_query(F.data.startswith("m2:done:"))
async def stage2_done(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    key = call.data.split(":")[2] + "_done"

    await db.mark_stage2(user_id, key)
    progress = await db.get_stage2(user_id)

    # show remaining
    missing = []
    if not progress.get("matn_done"):
        missing.append("📘 Матн")
    if not progress.get("audio_done"):
        missing.append("🎧 Аудио")
    if not progress.get("video_done"):
        missing.append("🎥 Видео")
    if not progress.get("links_done"):
        missing.append("🔗 Линклар")

    if missing:
        msg = "✅ Сақланди!\n\nҚолгани: " + ", ".join(missing)
    else:
        msg = "✅ Ҳаммаси тайёр! Энди ➡️ <b>Давом этиш</b> ни босинг."

    await call.message.answer(
        msg,
        reply_markup=kb_material_menu(progress)
    )


@dp.callback_query(F.data == "m2:locked")
async def stage2_locked(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    progress = await db.get_stage2(user_id)

    missing = []
    if not progress.get("matn_done"):
        missing.append("📘 Матн")
    if not progress.get("audio_done"):
        missing.append("🎧 Аудио")
    if not progress.get("video_done"):
        missing.append("🎥 Видео")
    if not progress.get("links_done"):
        missing.append("🔗 Линклар")

    await call.message.answer("🔒 Аввал қуйидагиларни тугатинг:\n" + "\n".join(missing))


@dp.callback_query(F.data == "m2:continue")
async def stage2_continue(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id

    # hard gate again (safety)
    progress = await db.get_stage2(user_id)
    all_done = all([
        progress.get("matn_done"),
        progress.get("audio_done"),
        progress.get("video_done"),
        progress.get("links_done"),
    ])
    if not all_done:
        return await call.message.answer("🔒 Аввал 4 та материални тўлиқ кўриб чиқинг.")

    await db.reset_stage3(user_id)
    await db.set_state(user_id, STAGE3_INTRO)

    await call.message.answer(
        "🎧 <b>3-босқич: Ишни бошлаш учун тўлиқ дарслик</b>\n\n"
        "Ҳозир сизга <b>11 та</b> аудио кетма-кет берилади.\n"
        "Ҳар аудиодан кейин: <b>Нимани тушундингиз?</b> деб сўрайман.\n\n"
        "Бошлаймиз ✅",
        reply_markup=kb_stage3_start()
    )


# ======================
# STAGE 3 SEND AUDIO
# ======================
async def send_stage3_audio(message_or_call, user_id: int, idx: int):
    # idx is 0-based
    filename = STAGE3_AUDIO_FILES[idx]
    path = STAGE3_DIR / filename

    if not path.exists():
        # Show full path to debug
        txt = (
            "❌ <b>Аудио файл топилмади.</b>\n\n"
            f"Керакли файл: <code>{filename}</code>\n"
            f"Йўл: <code>{path}</code>\n\n"
            "Файл номи ва папкаси тўғрилигини текширинг."
        )
        if isinstance(message_or_call, Message):
            await message_or_call.answer(txt)
        else:
            await message_or_call.message.answer(txt)
        return

    # mark waiting comment
    await db.set_stage3_waiting(user_id, True)
    await db.set_state(user_id, STAGE3_WAIT_COMMENT)

    caption = f"🎧 <b>{idx+1}-аудио</b>\n\nИлоҳим тинглаб бўлгач, изоҳ ёзинг: <b>Нимани тушундингиз?</b>"
    file = FSInputFile(path)

    if isinstance(message_or_call, Message):
        await message_or_call.answer_audio(file, caption=caption)
    else:
        await message_or_call.message.answer_audio(file, caption=caption)


@dp.callback_query(F.data == "s3:start")
async def stage3_start(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id

    flow = await db.get_stage3_flow(user_id)
    idx = flow["current_idx"]

    # Start from idx=0
    await db.set_stage3_idx(user_id, 0)
    await send_stage3_audio(call, user_id, 0)


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
