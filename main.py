# main.py
import asyncio
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode

import db
from config import BOT_TOKEN, DATABASE_URL, NEXT_BOT_LINK, ADMIN_IDS
from keyboards import (
    kb_start, kb_contact, kb_levels, kb_confirm, kb_edit_fields,
    kb_material_menu, kb_done_button, kb_stage3_start
)

BASE_DIR = Path(__file__).resolve().parent
STAGE2_DIR = BASE_DIR / "content" / "stage4"   # 2-bosqich material shu yerdan olinadi
STAGE3_DIR = BASE_DIR / "content" / "stage3"

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
STAGE3_WAIT_NOTE = "STAGE3_WAIT_NOTE"
DONE = "DONE"

# Stage3 audio list
STAGE3_AUDIO_FILES = [
    "1-ASOS.mp3",
    "2-ASOS-COVER.mp3",
    "3-ASOS-COVER.mp3",
    "4-ASOS.mp3",
    "5-ASOS.mp3",
    "6-ASOS.mp3",
    "7-ASOS.mp3",
    "8-ASOS.mp3",
    "9-ASOS.mp3",
    "10-ASOS DARSLIGI.mp3",
    "10-ASOS-2.mp3",
]

bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()


# ======================
# HELPERS
# ======================
def normalize_stage2(progress) -> dict:
    """progress None bo'lsa ham, har doim 4 key qaytarsin (KeyError bo'lmasin)."""
    if not isinstance(progress, dict):
        progress = {}
    return {
        "text_done": bool(progress.get("text_done", False)),
        "audio_done": bool(progress.get("audio_done", False)),
        "video_done": bool(progress.get("video_done", False)),
        "links_done": bool(progress.get("links_done", False)),
    }

def is_admin(user_id: int) -> bool:
    return user_id in (ADMIN_IDS or [])

async def admin_notify(text: str):
    if not ADMIN_IDS:
        return
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, text)
        except:
            pass

def stage2_remaining_list(progress: dict) -> list[str]:
    progress = normalize_stage2(progress)
    rem = []
    if not progress["text_done"]:
        rem.append("📘 Матн")
    if not progress["audio_done"]:
        rem.append("🎧 Аудио")
    if not progress["video_done"]:
        rem.append("🎥 Видео")
    if not progress["links_done"]:
        rem.append("🔗 Линклар")
    return rem


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
# ADMIN
# ======================
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    items = await db.get_users_overview(limit=30)
    if not items:
        return await message.answer("Ҳозирча фойдаланувчи йўқ.")
    lines = ["<b>Сўнгги 30 фойдаланувчи:</b>\n"]
    for u in items:
        s2 = []
        s2.append("✅" if u["stage2_text_done"] else "⬜")
        s2.append("✅" if u["stage2_audio_done"] else "⬜")
        s2.append("✅" if u["stage2_video_done"] else "⬜")
        s2.append("✅" if u["stage2_links_done"] else "⬜")
        lines.append(
            f"👤 <b>{u['full_name'] or '—'}</b> | <code>{u['user_id']}</code>\n"
            f"📌 state: <code>{u['state']}</code>\n"
            f"2-босқич: {''.join(s2)} | 3-босқич idx: <b>{u['stage3_idx']}</b>\n"
            "—"
        )
    lines.append("\n<b>Хабар юбориш:</b>\n<code>/send USER_ID матн</code>")
    await message.answer("\n".join(lines))

@dp.message(Command("send"))
async def cmd_send(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return await message.answer("Формат: <code>/send USER_ID матн</code>")
    if not parts[1].isdigit():
        return await message.answer("USER_ID рақам бўлиши керак.")
    uid = int(parts[1])
    txt = parts[2]
    try:
        await bot.send_message(uid, f"📩 <b>Админдан хабар:</b>\n\n{txt}")
        await message.answer("✅ Юборилди.")
    except Exception as e:
        await message.answer(f"❌ Юборилмади: {e}")


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

    await db.set_state(user_id, "")  # startda state bo'sh bo'lishi mumkin
    await message.answer(
        "🤖 <b>XJ расмий бот тизимига хуш келибсиз!</b>\n\n"
        "Бу ерда сиз рўйхатдан ўтасиз ва ишни босқичма-босқич бошлайсиз.\n\n"
        "Бошлаш учун тугмани босинг 👇",
        reply_markup=kb_start()
    )
    await admin_notify(f"🟢 /start: <code>{user_id}</code>")

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

    # 1️⃣ Ism-familiya
    if state == REG_NAME:
        if len(text) < 3:
            return await message.answer("Илтимос, исм-фамилияни тўлиқроқ ёзинг.")
        await db.set_user_field(user_id, "full_name", text)
        await db.set_state(user_id, REG_XJ_ID)
        await admin_notify(f"📝 1-босқич: {text} | <code>{user_id}</code>")
        return await message.answer("Раҳмат ✅\n\nЭнди XJ ID ни киритинг (7 хонали).")

    # 2️⃣ XJ ID
    if state == REG_XJ_ID:
        if not (text.isdigit() and len(text) == 7):
            return await message.answer("XJ ID 7 хонали рақам бўлиши керак.\nМасалан: 0123456")
        await db.set_user_field(user_id, "xj_id", text)
        await db.set_state(user_id, REG_JOIN_DATE)
        await admin_notify(f"📝 XJ ID: {text} | <code>{user_id}</code>")
        return await message.answer("Қабул қилинди ✅\n\nXJ га қачон қўшилгансиз? (эркин ёзинг)")

    # 3️⃣ Qo‘shilgan vaqt
    if state == REG_JOIN_DATE:
        await db.set_user_field(user_id, "join_date_text", text)
        await db.set_state(user_id, REG_PHONE)
        await admin_notify(f"📝 Қўшилган вақт: {text} | <code>{user_id}</code>")
        return await message.answer(
            "Тушунарли ✅\n\nЭнди телефон рақамингизни юборинг 👇",
            reply_markup=kb_contact()
        )

    # 3-bosqich izoh
    if state == STAGE3_WAIT_NOTE:
        idx = await db.get_stage3_idx(user_id)
        await db.save_stage3_note(user_id, idx, text)
        await db.set_stage3_waiting(user_id, False)

        await admin_notify(f"🎧 3-босқич изоҳ | idx={idx+1} | <code>{user_id}</code>\n📝 {text}")

        next_idx = idx + 1
        if next_idx >= len(STAGE3_AUDIO_FILES):
            await db.set_stage3_completed(user_id, True)
            await db.set_state(user_id, DONE)

            msg = "✅ <b>Сиз тўлиқ дарсликни олдингиз!</b>\n\n"
            if NEXT_BOT_LINK:
                msg += f"Энди навбатдаги босқичга ўтасиз 👇\n{NEXT_BOT_LINK}"
            else:
                msg += "Админ сиз билан боғланади."
            return await message.answer(msg)

        await db.set_stage3_idx(user_id, next_idx)
        return await send_stage3_audio(message, user_id, next_idx)


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
        await admin_notify(f"📞 Телефон: {message.contact.phone_number} | <code>{user_id}</code>")
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
        f"👤 Исм: {profile.get('full_name','')}\n"
        f"🆔 XJ ID: {profile.get('xj_id','')}\n"
        f"📅 Қўшилган вақт: {profile.get('join_date_text','')}\n"
        f"📞 Телефон: {profile.get('phone','')}\n"
        f"⭐ Даража: {profile.get('level','')}\n\n"
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

    # ✅ MUHIM: progress har doim 4 key bilan bo'lsin
    progress = normalize_stage2(await db.get_stage2(user_id))

    await admin_notify(f"✅ Рўйхатдан ўтди: <code>{user_id}</code>")

    await call.message.answer(
        "🎉 <b>Рўйхатдан муваффақиятли ўтдингиз!</b>\n\n"
        "Энди XJ билан тўлиқ танишиб чиқамиз.",
        reply_markup=kb_material_menu(progress)
    )

@dp.callback_query(F.data == "reg:confirm:edit")
async def reg_confirm_edit(call: CallbackQuery):
    await call.answer()
    await call.message.answer(
        "Қайси маълумотни ўзгартирасиз?",
        reply_markup=kb_edit_fields()
    )


# ======================
# STAGE 2 MATERIALS (content/stage4)
# ======================
async def stage2_send_text(call: CallbackQuery):
    path = STAGE2_DIR / "XJXJ_Kompaniyasi_Tanishtiruv.txt"
    if not path.exists():
        return await call.message.answer("❌ Матн файли топилмади.")
    content = path.read_text(encoding="utf-8", errors="ignore")
    await call.message.answer(
        f"📘 <b>XJ компанияси ҳақида</b>\n\n{content}",
        reply_markup=kb_done_button("✅ Ўқидим", "m2:done:text")
    )

async def stage2_send_audio(call: CallbackQuery):
    path = STAGE2_DIR / "xjaudio.mp3"
    if not path.exists():
        return await call.message.answer("❌ Аудио файли топилмади.")
    await call.message.answer_audio(
        audio=FSInputFile(path),
        caption="🎧 <b>XJ ҳақида аудио тушунтириш</b>",
        reply_markup=kb_done_button("✅ Тингладим", "m2:done:audio")
    )

async def stage2_send_video(call: CallbackQuery):
    path = STAGE2_DIR / "XJVIDEO.MOV"
    if not path.exists():
        return await call.message.answer("❌ Видео файли топилмади.")
    await call.message.answer_document(
        document=FSInputFile(path),
        caption="🎥 <b>XJ компанияси ҳақида видео</b>",
        reply_markup=kb_done_button("✅ Кўрдим", "m2:done:video")
    )

async def stage2_send_links(call: CallbackQuery):
    # ✅ sizdagi real nom: xjx_link.txt
    path = STAGE2_DIR / "xjx_link.txt"
    if not path.exists():
        return await call.message.answer("❌ Линклар файли топилмади.")
    content = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not content:
        content = "—"
    await call.message.answer(
        f"🔗 <b>Фойдали ҳаволалар:</b>\n{content}",
        reply_markup=kb_done_button("✅ Кўрдим", "m2:done:links")
    )

@dp.callback_query(F.data.startswith("m2:open:"))
async def stage2_open(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    item = call.data.split(":")[2]

    await admin_notify(f"📂 2-босқич очди: {item} | <code>{user_id}</code>")

    if item == "text":
        return await stage2_send_text(call)
    if item == "audio":
        return await stage2_send_audio(call)
    if item == "video":
        return await stage2_send_video(call)
    if item == "links":
        return await stage2_send_links(call)

@dp.callback_query(F.data.startswith("m2:done:"))
async def stage2_done(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    key = call.data.split(":")[2] + "_done"  # text_done ...

    await db.mark_stage2(user_id, key)

    progress = normalize_stage2(await db.get_stage2(user_id))
    rem = stage2_remaining_list(progress)

    await admin_notify(
        f"✅ 2-босқич тасдиқ: {key} | <code>{user_id}</code>\n"
        f"Қолди: {', '.join(rem) if rem else 'Йўқ'}"
    )

    msg = "Сақланди ✅"
    if rem:
        msg += "\n\n<b>Қолди:</b> " + ", ".join(rem)
    else:
        msg += "\n\n🎉 <b>Ҳаммаси тайёр!</b> Энди ➡️ <b>Давом этиш</b> ни босинг."

    await call.message.answer(msg, reply_markup=kb_material_menu(progress))

@dp.callback_query(F.data == "m2:continue_locked")
async def stage2_continue_locked(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    progress = normalize_stage2(await db.get_stage2(user_id))
    rem = stage2_remaining_list(progress)
    await call.message.answer(
        "🔒 Ҳали ҳаммаси кўрилмаган.\n\n<b>Қолди:</b> " + ", ".join(rem),
        reply_markup=kb_material_menu(progress)
    )

@dp.callback_query(F.data == "m2:continue")
async def stage2_continue(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    if not await db.stage2_all_done(user_id):
        progress = normalize_stage2(await db.get_stage2(user_id))
        rem = stage2_remaining_list(progress)
        return await call.message.answer(
            "🔒 Ҳали ҳаммаси кўрилмаган.\n\n<b>Қолди:</b> " + ", ".join(rem),
            reply_markup=kb_material_menu(progress)
        )

    await db.set_state(user_id, STAGE3_INTRO)
    await admin_notify(f"➡️ 3-босқичга ўтди: <code>{user_id}</code>")

    await call.message.answer(
        "🎧 <b>3-босқич: Ишни бошлаш учун тўлиқ дарслик</b>\n\n"
        "Ҳозир сизга 11 та аудио кетма-кет берилади.\n"
        "Ҳар аудиодан кейин: <b>Нимани тушундингиз?</b> деб сўрайман.\n\n"
        "Бошлаймиз ✅",
        reply_markup=kb_stage3_start()
    )


# ======================
# STAGE 3
# ======================
async def send_stage3_audio(message: Message, user_id: int, idx: int):
    fname = STAGE3_AUDIO_FILES[idx]
    path = STAGE3_DIR / fname
    if not path.exists():
        await admin_notify(f"❌ 3-босқич аудио топилмади: {fname} | <code>{user_id}</code>")
        return await message.answer(
            "❌ Аудио файл топилмади.\n\n"
            f"Керакли файл: <code>{fname}</code>\n"
            f"Йўл: <code>{path.as_posix()}</code>\n\n"
            "Файл номи ва папкаси тўғрилигини текширинг."
        )

    await message.answer_audio(
        audio=FSInputFile(path),
        caption=(
            f"🎧 <b>{idx+1}-аудио</b>\n\n"
            "Илтимос тинглаб бўлгач, изоҳ ёзинг:\n"
            "<b>Нимани тушундингиз?</b>"
        )
    )
    await db.set_stage3_waiting(user_id, True)
    await db.set_state(user_id, STAGE3_WAIT_NOTE)

@dp.callback_query(F.data == "s3:start")
async def stage3_start(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    await db.set_stage3_idx(user_id, 0)
    await admin_notify(f"🎧 3-босқич бошланди: <code>{user_id}</code>")
    await send_stage3_audio(call.message, user_id, 0)


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
