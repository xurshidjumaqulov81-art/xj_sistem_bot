# main.py
import asyncio
import json
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile

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
STAGE3_SEND_PREFIX = "ST3_SEND_"   # ST3_SEND_1
STAGE3_WAIT_PREFIX = "ST3_WAIT_"   # ST3_WAIT_1
STAGE3_DONE = "STAGE3_DONE"

# ======================
# Stage 3 audio files (SIZDAGI NOMLARGA MOSLAB QO‘YING)
# Papka: content/stage3/
# ======================
STAGE3_FILES = [
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
    "10-ASOS-2.mp3",  # sizda shunaqa bo‘lsa, qoldiring
\]

BASE_DIR = Path(__file__).resolve().parent
STAGE3_DIR = BASE_DIR / "content" / "stage3"

NEXT_BOT_LINK = os.getenv("NEXT_BOT_LINK", "https://t.me/your_next_bot_username")

# ======================
bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()


# ======================
# HELPERS
# ======================
def _stage3_state_send(i: int) -> str:
    return f"{STAGE3_SEND_PREFIX}{i}"

def _stage3_state_wait(i: int) -> str:
    return f"{STAGE3_WAIT_PREFIX}{i}"

def _parse_stage3_wait(state: str) -> int | None:
    if state.startswith(STAGE3_WAIT_PREFIX):
        try:
            return int(state.replace(STAGE3_WAIT_PREFIX, ""))
        except:
            return None
    return None

def _parse_stage3_send(state: str) -> int | None:
    if state.startswith(STAGE3_SEND_PREFIX):
        try:
            return int(state.replace(STAGE3_SEND_PREFIX, ""))
        except:
            return None
    return None

def _stage2_missing(progress: dict) -> list[str]:
    missing = []
    if not progress.get("matn_done"):
        missing.append("Матн")
    if not progress.get("audio_done"):
        missing.append("Аудио")
    if not progress.get("video_done"):
        missing.append("Видео")
    if not progress.get("links_done"):
        missing.append("Линклар")
    return missing


async def stage3_send_audio_and_ask(user_id: int, message: Message, lesson_index: int):
    """
    lesson_index: 1..11
    """
    # validate range
    if lesson_index < 1 or lesson_index > len(STAGE3_FILES):
        return

    filename = STAGE3_FILES[lesson_index - 1]
    path = STAGE3_DIR / filename

    if not path.exists():
        await message.answer(
            "❌ <b>Аудио файл топилмади.</b>\n\n"
            f"Керакли файл: <code>{filename}</code>\n"
            f"Кутилаётган жой: <code>content/stage3/{filename}</code>\n\n"
            "Файл номи ва папкаси тўғри эканини текширинг."
        )
        return

    # Send audio
    await message.answer(
        f"🎧 <b>{lesson_index}-аудио</b>\n"
        "Эшитиб бўлгач, изоҳ ёзинг:"
    )
    await message.answer_audio(FSInputFile(str(path)))

    # Ask comment
    await message.answer("✍️ <b>Нимани тушундингиз?</b>\nИзоҳни ёзинг (эркин матн).")

    # set state to WAIT lesson
    await db.set_state(user_id, _stage3_state_wait(lesson_index))


async def stage3_save_comment(user_id: int, lesson_index: int, comment: str):
    """
    Stage3 comments are saved inside stage3_progress.confirmed_text as JSON.
    No schema change needed.
    """
    # read old
    row = await db.fetchrow("SELECT confirmed_text FROM stage3_progress WHERE user_id=$1", user_id)
    data = {}
    if row and row["confirmed_text"]:
        try:
            data = json.loads(row["confirmed_text"])
        except:
            data = {}

    data[str(lesson_index)] = comment

    # upsert
    await db.execute("""
        INSERT INTO stage3_progress(user_id, confirmed_text, confirmed_at)
        VALUES($1, $2, NOW())
        ON CONFLICT (user_id)
        DO UPDATE SET confirmed_text=EXCLUDED.confirmed_text, confirmed_at=EXCLUDED.confirmed_at
    """, user_id, json.dumps(data, ensure_ascii=False))


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
        try:
            inviter_id = await db.get_user_id_by_ref_code(ref_code)
        except:
            inviter_id = None

    # ensure user exists
    try:
        await db.ensure_user(user_id, inviter_id)
    except TypeError:
        # if your db.ensure_user(user_id) only accepts 1 arg
        await db.ensure_user(user_id)

    await message.answer(
        "🤖 <b>XJ расмий бот тизимига хуш келибсиз!</b>\n\n"
        "Бу ерда сиз рўйхатдан ўтасиз ва ишни босқичма-босқич бошлайсиз.\n\n"
        "Бошлаш учун тугмани босинг 👇",
        reply_markup=kb_start()
    )


@dp.callback_query(F.data == "start:begin")
async def start_begin(call: CallbackQuery):
    await call.answer()
    await db.set_state(call.from_user.id, REG_NAME)
    await call.message.answer("✅ Рўйхатдан ўтишни бошлаймиз.\n\nИсм-фамилиянгизни ёзинг.")


# ======================
# NOOP
# ======================
@dp.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()


# ======================
# TEXT HANDLER
# ======================
@dp.message(F.text)
async def text_handler(message: Message):
    user_id = message.from_user.id
    state = await db.get_state(user_id)
    text = message.text.strip()

    # 1) REG_NAME
    if state == REG_NAME:
        if len(text) < 3:
            return await message.answer("Илтимос, исм-фамилияни тўлиқроқ ёзинг.")
        await db.set_user_field(user_id, "full_name", text)
        await db.set_state(user_id, REG_XJ_ID)
        return await message.answer("✅ Раҳмат.\n\nЭнди XJ ID ни киритинг (7 хонали).")

    # 2) REG_XJ_ID
    if state == REG_XJ_ID:
        if not (text.isdigit() and len(text) == 7):
            return await message.answer("XJ ID 7 хонали рақам бўлиши керак.\nМасалан: 0123456")
        await db.set_user_field(user_id, "xj_id", text)
        await db.set_state(user_id, REG_JOIN_DATE)
        return await message.answer("✅ Қабул қилинди.\n\nXJ га қачон қўшилгансиз? (эркин ёзинг)")

    # 3) REG_JOIN_DATE
    if state == REG_JOIN_DATE:
        await db.set_user_field(user_id, "join_date_text", text)
        await db.set_state(user_id, REG_PHONE)
        return await message.answer(
            "✅ Тушунарли.\n\nЭнди телефон рақамингизни юборинг 👇",
            reply_markup=kb_contact()
        )

    # ======================
    # STAGE 3: WAIT COMMENT
    # ======================
    wait_i = _parse_stage3_wait(state)
    if wait_i is not None:
        if len(text) < 1:
            return await message.answer("Илтимос, камида 1 та сўз ёзинг.")

        # save comment
        await stage3_save_comment(user_id, wait_i, text)

        # next
        next_i = wait_i + 1
        if next_i <= len(STAGE3_FILES):
            await message.answer(f"✅ Қабул қилинди. ({wait_i}/{len(STAGE3_FILES)})\n\nКейингиси 👇")
            return await stage3_send_audio_and_ask(user_id, message, next_i)

        # done
        await db.set_state(user_id, STAGE3_DONE)
        return await message.answer(
            "🎉 <b>Сиз тўлиқ дарсликни олдингиз!</b>\n\n"
            "Энди навбатдаги босқичга чиқасиз.\n"
            "Қуйидаги ботга ўтинг 👇\n\n"
            f"🔗 {NEXT_BOT_LINK}"
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
            "✅ Раҳмат.\n\nДаражангизни танланг:",
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
        "Маълумотларни текширинг:\n\n"
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
        "Энди XJ билан тўлиқ танишиб чиқамиз.",
        reply_markup=kb_material_menu(progress)
    )


@dp.callback_query(F.data == "reg:confirm:edit")
async def reg_confirm_edit(call: CallbackQuery):
    await call.answer()
    await call.message.answer(
        "Қайси маълумотни ўзгартирмоқчисиз?",
        reply_markup=kb_edit_fields()
    )


# ======================
# STAGE 2 MATERIALS
# ======================
@dp.callback_query(F.data.startswith("m2:open:"))
async def stage2_open(call: CallbackQuery):
    await call.answer()
    item = call.data.split(":")[2]

    if item == "text":
        await call.message.answer(
            "📘 <b>XJ компанияси ҳақида</b>\n\n"
            "(XJ ҳақида тўлиқ матн шу ерда бўлади)",
            reply_markup=kb_done_button("✅ Ўқидим", "m2:done:matn")
        )

    elif item == "audio":
        await call.message.answer(
            "🎧 <b>XJ ҳақида аудио тушунтириш</b>\n\n(бу ерда аудио бўлади)",
            reply_markup=kb_done_button("✅ Тингладим", "m2:done:audio")
        )

    elif item == "video":
        await call.message.answer(
            "🎥 <b>XJ компанияси ҳақида видео</b>\n\n(бу ерда видео ёки линк бўлади)",
            reply_markup=kb_done_button("✅ Кўрдим", "m2:done:video")
        )

    elif item == "links":
        await call.message.answer(
            "🔗 <b>Фойдали ҳаволалар:</b>\n"
            "— Расмий сайт\n"
            "— Telegram\n"
            "— Instagram",
            reply_markup=kb_done_button("✅ Кўрдим", "m2:done:links")
        )


@dp.callback_query(F.data.startswith("m2:done:"))
async def stage2_done(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    key = call.data.split(":")[2] + "_done"  # matn_done/audio_done/video_done/links_done

    await db.mark_stage2(user_id, key)
    progress = await db.get_stage2(user_id)

    missing = _stage2_missing(progress)
    done_count = 4 - len(missing)

    msg = f"✅ Саҡланди\n🔒 Ҳолат: {done_count}/4"
    if missing:
        msg += "\nҚолганлар: " + ", ".join(missing)
    else:
        msg = "🎉 Ҳаммаси тайёр! Энди ➡️ Давом этиш ни босинг."

    await call.message.answer(msg, reply_markup=kb_material_menu(progress))


@dp.callback_query(F.data == "m2:continue_locked")
async def stage2_continue_locked(call: CallbackQuery):
    progress = await db.get_stage2(call.from_user.id)
    missing = _stage2_missing(progress)
    if not missing:
        return await call.answer()
    await call.answer("Аввал барчасини кўринг: " + ", ".join(missing), show_alert=True)


@dp.callback_query(F.data == "m2:continue")
async def stage2_continue(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    progress = await db.get_stage2(user_id)

    missing = _stage2_missing(progress)
    if missing:
        return await call.answer("Аввал барчасини кўринг: " + ", ".join(missing), show_alert=True)

    # Stage 3 start
    await db.set_state(user_id, _stage3_state_send(1))

    await call.message.answer(
        "🎧 <b>3-босқич: Ишни бошлаш учун тўлиқ дарслик</b>\n\n"
        f"Ҳозир сизга <b>{len(STAGE3_FILES)}</b> та аудио кетма-кет берилади.\n"
        "Ҳар аудиодан кейин: <b>Нимани тушундингиз?</b> деб сўрайман.\n\n"
        "Бошлаймиз ✅"
    )

    # send first lesson
    await stage3_send_audio_and_ask(user_id, call.message, 1)


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
