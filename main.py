# main.py
import asyncio
import os
from typing import Dict, Any, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, DATABASE_URL

# Sizdagi db.py modulida quyidagi funksiyalar bo‘lishi kerak:
# init(DATABASE_URL), close(),
# ensure_user(user_id, inviter_id=None),
# get_state(user_id), set_state(user_id, state),
# set_user_field(user_id, field, value),
# get_user_profile(user_id),
# mark_stage2(user_id, key), get_stage2(user_id)
# get_user_id_by_ref_code(ref_code) (ixtiyoriy)
import db


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

# Stage 3: comment states => "STAGE3_COMMENT_1" .. "STAGE3_COMMENT_11"
STAGE3_COMMENT_PREFIX = "STAGE3_COMMENT_"

# ======================
# CONFIG
# ======================
NEXT_BOT_LINK = os.getenv("NEXT_BOT_LINK", "").strip()
# Agar mp3 fayllar masalan "content/stage3/" ichida bo‘lsa: STAGE3_AUDIO_DIR = "content/stage3"
# Agar mp3 fayllar repoda rootda bo‘lsa: STAGE3_AUDIO_DIR = ""
STAGE3_AUDIO_DIR = os.getenv("STAGE3_AUDIO_DIR", "").strip()

# 3-bosqich audio ketma-ketligi (siz aytgan tartib)
# 1) 10-ASOS DARSligi
# 2) 1-ASOS
# 3) 2-ASOS ...
STAGE3_AUDIO_FILES: Dict[int, str] = {
    1: "10-ASOS DARSLIGI.mp3",
    2: "1-ASOS.mp3",
    3: "2-ASOS.mp3",
    4: "3-ASOS.mp3",
    5: "4-ASOS.mp3",
    6: "5-ASOS.mp3",
    7: "6-ASOS.mp3",
    8: "7-ASOS.mp3",
    9: "8-ASOS.mp3",
    10: "9-ASOS.mp3",
    11: "10-ASOS.mp3",
}

STAGE3_TOTAL = len(STAGE3_AUDIO_FILES)

# ======================
bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()


# ======================
# KEYBOARDS (inline)
# ======================
def kb_start():
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Бошлаш", callback_data="start:begin")
    return kb.as_markup()

def kb_contact():
    # Kontakt tugmasi ReplyKeyboard bo‘lishi mumkin, lekin aiogram v3 da oddiy text bilan ham yuradi.
    # Siz contact request qiladigan keyboard ishlatayotgan bo‘lsangiz, o‘sha eski keyboards.py dan foydalaning.
    # Bu yerda minimal variant: user o‘zi raqam yozib yuborsa ham ishlaydi.
    # Lekin siz oldin contact ishlatgansiz — shuning uchun pastda F.contact handler bor.
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Контакт юбориш", request_contact=True)]],
        resize_keyboard=True
    )

def kb_levels():
    kb = InlineKeyboardBuilder()
    kb.button(text="Оддий", callback_data="reg:level:oddiy")
    kb.button(text="Manager", callback_data="reg:level:manager")
    kb.button(text="Bronza", callback_data="reg:level:bronza")
    kb.button(text="Silver", callback_data="reg:level:silver")
    kb.adjust(2)
    return kb.as_markup()

def kb_confirm():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Тасдиқлайман", callback_data="reg:confirm:yes")
    kb.button(text="✏️ Ўзгартирмоқчиман", callback_data="reg:confirm:edit")
    kb.adjust(1)
    return kb.as_markup()

def kb_edit_fields():
    kb = InlineKeyboardBuilder()
    kb.button(text="Исм-фамилия", callback_data="edit:full_name")
    kb.button(text="XJ ID", callback_data="edit:xj_id")
    kb.button(text="Қўшилган вақт", callback_data="edit:join_date_text")
    kb.button(text="Телефон", callback_data="edit:phone")
    kb.button(text="Даража", callback_data="edit:level")
    kb.adjust(2)
    return kb.as_markup()

def kb_done_button(text: str, cb: str):
    kb = InlineKeyboardBuilder()
    kb.button(text=text, callback_data=cb)
    kb.adjust(1)
    return kb.as_markup()

def kb_stage2_menu(progress: Dict[str, bool]):
    matn = progress.get("matn_done", False)
    audio = progress.get("audio_done", False)
    video = progress.get("video_done", False)
    links = progress.get("links_done", False)

    kb = InlineKeyboardBuilder()
    kb.button(text=("✅ 📘 Матн" if matn else "📘 Матн"), callback_data="m2:open:text")
    kb.button(text=("✅ 🎧 Аудио" if audio else "🎧 Аудио"), callback_data="m2:open:audio")
    kb.button(text=("✅ 🎥 Видео" if video else "🎥 Видео"), callback_data="m2:open:video")
    kb.button(text=("✅ 🔗 Линклар" if links else "🔗 Линклар"), callback_data="m2:open:links")
    kb.adjust(2)

    # Gate: faqat 4/4 bo‘lsa continue
    if matn and audio and video and links:
        kb.button(text="➡️ Давом этиш", callback_data="m2:continue")
        kb.adjust(2, 2, 1)
    else:
        # continue yo‘q (majburiy)
        pass

    return kb.as_markup()

def kb_stage3_nextbot(link: str):
    kb = InlineKeyboardBuilder()
    if link:
        kb.button(text="➡️ Кейинги ботга ўтиш", url=link)
    return kb.as_markup()


# ======================
# HELPERS
# ======================
def stage3_audio_path(filename: str) -> str:
    if STAGE3_AUDIO_DIR:
        return os.path.join(STAGE3_AUDIO_DIR, filename)
    return filename

def stage3_comment_state(lesson: int) -> str:
    return f"{STAGE3_COMMENT_PREFIX}{lesson}"

def parse_stage3_lesson(state: str) -> Optional[int]:
    if not state.startswith(STAGE3_COMMENT_PREFIX):
        return None
    try:
        return int(state.replace(STAGE3_COMMENT_PREFIX, "").strip())
    except:
        return None

async def send_stage3_audio_and_ask_comment(message: Message, user_id: int, lesson: int):
    filename = STAGE3_AUDIO_FILES.get(lesson)
    if not filename:
        return

    path = stage3_audio_path(filename)

    # Audio fayl topilmasa - xatoni ko‘rsatamiz (Railway loglarida ham chiqadi)
    if not os.path.exists(path):
        await message.answer(
            "❌ Аудио файл топилмади.\n\n"
            f"<b>Керакли файл:</b> {filename}\n"
            f"<b>Йўл:</b> {path}\n\n"
            "Файл номи ва папкаси тўғрилигини текширинг."
        )
        return

    caption = (
        f"🎧 <b>Тўлиқ дарслик</b>\n\n"
        f"<b>{lesson}/{STAGE3_TOTAL}</b> — Аудиони тингланг.\n\n"
        "Тинглаб бўлгач, қуйидаги саволга жавоб ёзинг:\n"
        "👉 <b>Нимани тушундингиз?</b>"
    )

    await message.answer_audio(
        audio=FSInputFile(path),
        caption=caption
    )

    await db.set_state(user_id, stage3_comment_state(lesson))


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
        except Exception:
            inviter_id = None

    await db.ensure_user(user_id, inviter_id)

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
# TEXT HANDLER
# ======================
@dp.message(F.text)
async def text_handler(message: Message):
    user_id = message.from_user.id
    state = await db.get_state(user_id)
    text = message.text.strip()

    # 1) Исм-фамилия
    if state == REG_NAME:
        if len(text) < 3:
            return await message.answer("Илтимос, исм-фамилияни тўлиқроқ ёзинг.")
        await db.set_user_field(user_id, "full_name", text)
        await db.set_state(user_id, REG_XJ_ID)
        return await message.answer("✅ Раҳмат.\n\nЭнди XJ ID ни киритинг (7 хонали рақам).")

    # 2) XJ ID
    if state == REG_XJ_ID:
        if not (text.isdigit() and len(text) == 7):
            return await message.answer("XJ ID 7 хонали рақам бўлиши керак.\nМасалан: 0123456")
        await db.set_user_field(user_id, "xj_id", text)
        await db.set_state(user_id, REG_JOIN_DATE)
        return await message.answer("✅ Қабул қилинди.\n\nXJ га қачон қўшилгансиз? (эркин ёзинг)")

    # 3) Қўшилган вақт
    if state == REG_JOIN_DATE:
        await db.set_user_field(user_id, "join_date_text", text)
        await db.set_state(user_id, REG_PHONE)
        return await message.answer(
            "✅ Тушунарли.\n\nЭнди телефон рақамингизни контакт орқали юборинг 👇",
            reply_markup=kb_contact()
        )

    # Stage 3: izohlar
    lesson = parse_stage3_lesson(state)
    if lesson is not None:
        # Izoh bo‘sh bo‘lmasin
        if len(text) < 2:
            return await message.answer("Илтимос, камида 2 та белги билан изоҳ ёзинг.")

        # Izohni DB ga yozib qo‘yamiz (agar db.py da bunday jadval bo‘lmasa ham, ishlashi uchun try)
        # Siz xohlasangiz keyin db.py ga stage3_notes jadvalini qo‘shib beraman.
        try:
            await db.save_stage3_note(user_id, lesson, text)  # ixtiyoriy metod
        except Exception:
            pass

        next_lesson = lesson + 1
        if next_lesson <= STAGE3_TOTAL:
            return await send_stage3_audio_and_ask_comment(message, user_id, next_lesson)

        # Tugadi
        await db.set_state(user_id, "STAGE3_DONE")
        end_text = (
            "🎉 <b>Табриклайман!</b>\n\n"
            "Сиз тўлиқ дарсликни олдингиз ✅\n"
            "Энди навбатдаги босқичга чиқасиз."
        )
        return await message.answer(end_text, reply_markup=kb_stage3_nextbot(NEXT_BOT_LINK))


# ======================
# CONTACT HANDLER
# ======================
@dp.message(F.contact)
async def contact_handler(message: Message):
    user_id = message.from_user.id
    state = await db.get_state(user_id)

    if state == REG_PHONE:
        phone = message.contact.phone_number
        await db.set_user_field(user_id, "phone", phone)
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

    profile: Dict[str, Any] = await db.get_user_profile(user_id)

    text = (
        "Маълумотларингизни текширинг:\n\n"
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
        reply_markup=kb_stage2_menu(progress)
    )


@dp.callback_query(F.data == "reg:confirm:edit")
async def reg_confirm_edit(call: CallbackQuery):
    await call.answer()
    await call.message.answer("Қайси маълумотни ўзгартирмоқчисиз?", reply_markup=kb_edit_fields())


# ======================
# EDIT FIELDS (minimal)
# ======================
@dp.callback_query(F.data.startswith("edit:"))
async def edit_field(call: CallbackQuery):
    await call.answer()
    field = call.data.split(":")[1]
    user_id = call.from_user.id

    # Qaysi field bo‘lsa, o‘sha state ga qaytaramiz:
    if field == "full_name":
        await db.set_state(user_id, REG_NAME)
        return await call.message.answer("Исм-фамилиянгизни қайта ёзинг:")
    if field == "xj_id":
        await db.set_state(user_id, REG_XJ_ID)
        return await call.message.answer("XJ ID ни қайта ёзинг (7 хонали рақам):")
    if field == "join_date_text":
        await db.set_state(user_id, REG_JOIN_DATE)
        return await call.message.answer("Қачон қўшилгансиз? қайта ёзинг:")
    if field == "phone":
        await db.set_state(user_id, REG_PHONE)
        return await call.message.answer("Контактни қайта юборинг:", reply_markup=kb_contact())
    if field == "level":
        await db.set_state(user_id, REG_LEVEL)
        return await call.message.answer("Даражани қайта танланг:", reply_markup=kb_levels())


# ======================
# STAGE 2 MATERIALS
# ======================
@dp.callback_query(F.data.startswith("m2:open:"))
async def stage2_open(call: CallbackQuery):
    await call.answer()
    item = call.data.split(":")[2]

    if item == "text":
        return await call.message.answer(
            "📘 <b>XJ компанияси ҳақида</b>\n\n"
            "(XJ ҳақида тўлиқ матн шу ерда бўлади)",
            reply_markup=kb_done_button("✅ Ўқидим", "m2:done:matn")
        )

    if item == "audio":
        return await call.message.answer(
            "🎧 <b>XJ ҳақида аудио тушунтириш</b>\n\n"
            "(бу ерда аудио файл ёки линк бўлади)",
            reply_markup=kb_done_button("✅ Тингладим", "m2:done:audio")
        )

    if item == "video":
        return await call.message.answer(
            "🎥 <b>XJ компанияси ҳақида видео</b>\n\n"
            "(бу ерда видео ёки YouTube линк бўлади)",
            reply_markup=kb_done_button("✅ Кўрдим", "m2:done:video")
        )

    if item == "links":
        return await call.message.answer(
            "🔗 <b>Фойдали ҳаволалар</b>\n"
            "— Расмий сайт\nToggle\n— Телеграм\n— Инстаграм",
            reply_markup=kb_done_button("✅ Кўрдим", "m2:done:links")
        )


@dp.callback_query(F.data.startswith("m2:done:"))
async def stage2_done(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    key = call.data.split(":")[2] + "_done"  # matn_done / audio_done / video_done / links_done

    await db.mark_stage2(user_id, key)
    progress = await db.get_stage2(user_id)

    # Gate tekshiruvi shu yerda ham aniq ko‘rinadi
    if progress.get("matn_done") and progress.get("audio_done") and progress.get("video_done") and progress.get("links_done"):
        await call.message.answer("✅ Ҳаммаси тайёр! Энди ➡️ Давом этиш ни босинг.", reply_markup=kb_stage2_menu(progress))
    else:
        await call.message.answer("Сақланди ✅", reply_markup=kb_stage2_menu(progress))


@dp.callback_query(F.data == "m2:continue")
async def stage2_continue(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id

    progress = await db.get_stage2(user_id)
    # Majburiy gate
    if not (progress.get("matn_done") and progress.get("audio_done") and progress.get("video_done") and progress.get("links_done")):
        return await call.message.answer(
            "🔒 Аввал 4 та материални ҳам кўриб чиқинг:\n"
            "📘 Матн, 🎧 Аудио, 🎥 Видео, 🔗 Линклар"
        )

    # Stage 3 boshlanadi
    await call.message.answer(
        "🎧 <b>3-босқич: Ишни бошлаш учун тўлиқ дарслик</b>\n\n"
        "Ҳозир сизга 11 та аудио кетма-кет берилади.\n"
        "Ҳар аудиодан кейин: <b>Нимани тушундингиз?</b> деб сўрайман.\n\n"
        "Бошлаймиз ✅"
    )

    # 1-audio
    await send_stage3_audio_and_ask_comment(call.message, user_id, 1)


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
