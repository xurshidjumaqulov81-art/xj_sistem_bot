import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from db import get_stage2, set_stage2_done, upsert_user

from db import (
    init_db,
    get_user,
    upsert_user,
    get_stage2,
    set_stage2_done
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
dp = Dispatcher()

# ====== Vaqtinchalik xotira (keyin DB qilamiz) ======
user_stage: dict[int, str] = {}   # qaysi qadamda
data_store: dict[int, dict] = {}  # user ma'lumotlari

ST_FULLNAME = "reg_fullname"
ST_XJID = "reg_xjid"
ST_JOIN = "reg_join"
ST_PHONE = "reg_phone"
ST_LEVEL = "reg_level"
ST_CONFIRM = "reg_confirm"
ST_EDIT_MENU = "reg_edit_menu"

LEVELS = ["Oddiy", "Manager", "Bronza", "Silver"]

def get_user(uid: int) -> dict:
    if uid not in data_store:
        data_store[uid] = {
            "full_name": None,
            "xj_id": None,
            "join_date_text": None,
            "phone": None,
            "level": None
        }
    return data_store[uid]

def level_kb():
    kb = InlineKeyboardBuilder()
    for lv in LEVELS:
        kb.button(text=lv, callback_data=f"level:{lv}")
    kb.adjust(2)
    return kb.as_markup()

def confirm_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlayman", callback_data="confirm:yes")
    kb.button(text="✏️ O‘zgartirmoqchiman", callback_data="confirm:edit")
    kb.adjust(1)
    return kb.as_markup()

def edit_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Ism-familiya", callback_data="edit:full_name")
    kb.button(text="XJ ID", callback_data="edit:xj_id")
    kb.button(text="Qo‘shilgan vaqt", callback_data="edit:join")
    kb.button(text="Telefon", callback_data="edit:phone")
    kb.button(text="Daraja", callback_data="edit:level")
    kb.adjust(2)
    return kb.as_markup()

def contact_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Kontakt yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def format_summary(u: dict) -> str:
    phone = u["phone"] or "-"
    return (
        "Ma’lumotlaringizni tekshiring:\n"
        f"Ism-familiya: {u['full_name'] or '-'}\n"
        f"XJ ID: {u['xj_id'] or '-'}\n"
        f"XJga qo‘shilgan vaqt: {u['join_date_text'] or '-'}\n"
        f"Telefon: {phone}\n"
        f"Daraja: {u['level'] or '-'}\n\n"
        "Tasdiqlaysizmi?"
    )

# ====== START ======
@dp.message(F.text == "/start")
async def cmd_start(m: Message):
    await m.answer(
        "XJ rasmiy bot tizimiga xush kelibsiz! 👋\n\n"
        "Boshlash uchun 'Start' deb yozing."
    )

@dp.message(F.text.lower() == "start")
async def start_registration(m: Message):
    uid = m.from_user.id
    get_user(uid)  # init
    user_stage[uid] = ST_FULLNAME
    await m.answer("Ro‘yxatdan o‘tishni boshlaymiz ✅\nIltimos, ism-familiyangizni yozing.")

# ====== TEXT ROUTER ======
@dp.message(F.text)
async def text_router(m: Message):
    uid = m.from_user.id
    stage = user_stage.get(uid)
    u = get_user(uid)

    # 1) FULL NAME
    if stage == ST_FULLNAME:
        full_name = m.text.strip()
        if len(full_name) < 3:
            await m.answer("Iltimos, ism-familiyangizni to‘liq yozing 🙂")
            return
        u["full_name"] = full_name
        user_stage[uid] = ST_XJID
        await m.answer(
            f"Rahmat, {full_name} ✅\n"
            "Endi XJ ID ni kiriting (7 xonali raqam).\n"
            "Masalan: 0123456"
        )
        return

    # 2) XJ ID (7 digits)
    if stage == ST_XJID:
        xj_id = m.text.strip()
        if not (xj_id.isdigit() and len(xj_id) == 7):
            await m.answer("Iltimos 7 xonali raqam kiriting. Masalan: 0123456")
            return
        u["xj_id"] = xj_id
        user_stage[uid] = ST_JOIN
        await m.answer(
            "Qabul qilindi ✅\n"
            "Endi: XJ ga qachon qo‘shilgansiz?\n"
            "Aniq sana bo‘lsa: YYYY-MM-DD\n"
            "Yo‘q bo‘lsa: 2024 oxiri / taxminan 3 oy oldin / bilmayman"
        )
        return

    # 3) JOIN DATE (free text)
    if stage == ST_JOIN:
        join_text = m.text.strip()
        if len(join_text) < 2:
            await m.answer("Iltimos, kamida biror narsa yozing (masalan: 2024 oxiri).")
            return
        u["join_date_text"] = join_text
        user_stage[uid] = ST_PHONE
        await m.answer(
            "Tushunarli ✅\nEndi telefon raqamingizni yuboring.\nPastdagi tugma orqali kontakt ulashing.",
            reply_markup=contact_kb()
        )
        return

    # Agar user phone bosqichida turib telefonni matn qilib yuborsa ham qabul qilamiz
    if stage == ST_PHONE:
        phone_text = m.text.strip()
        if len(phone_text) < 5:
            await m.answer("Iltimos kontakt yuboring yoki raqamni to‘liq yozing.")
            return
        u["phone"] = phone_text
        user_stage[uid] = ST_LEVEL
        await m.answer("Rahmat ✅\nEndi darajangizni tanlang:", reply_markup=level_kb())
        return

    # Default
    await m.answer("Boshlash uchun /start bosing, keyin 'Start' deb yozing.")

# ====== CONTACT HANDLER ======
@dp.message(F.contact)
async def contact_handler(m: Message):
    uid = m.from_user.id
    stage = user_stage.get(uid)
    u = get_user(uid)

    if stage != ST_PHONE:
        await m.answer("Kontakt qabul qilindi, lekin hozir bu bosqich emas. /start dan boshlang.")
        return

    phone = m.contact.phone_number
    if phone and not phone.startswith("+"):
        phone = "+" + phone
    u["phone"] = phone
    user_stage[uid] = ST_LEVEL
    await m.answer("Rahmat ✅\nEndi darajangizni tanlang:", reply_markup=level_kb())

# ====== LEVEL CALLBACK ======
@dp.callback_query(F.data.startswith("level:"))
async def level_pick(cb: CallbackQuery):
    uid = cb.from_user.id
    stage = user_stage.get(uid)
    u = get_user(uid)

    if stage != ST_LEVEL:
        await cb.answer("Bu bosqich hozir aktiv emas.", show_alert=False)
        return

    level = cb.data.split("level:", 1)[1]
    u["level"] = level
    user_stage[uid] = ST_CONFIRM

    await cb.message.answer(format_summary(u), reply_markup=confirm_kb())
    await cb.answer()

# ====== CONFIRM / EDIT ======
@dp.callback_query(F.data == "confirm:yes")
async def confirm_yes(cb: CallbackQuery):
    uid = cb.from_user.id
    u = get_user(uid)
    user_stage[uid] = "done"

    await cb.message.answer(
        "Tabriklayman! Ro‘yxatdan muvaffaqiyatli o‘tdingiz ✅🎉\n"
        "Keyingi bosqichga o‘tamiz."
    )
    await cb.answer()

@dp.callback_query(F.data == "confirm:edit")
async def confirm_edit(cb: CallbackQuery):
    uid = cb.from_user.id
    user_stage[uid] = ST_EDIT_MENU
    await cb.message.answer("Qaysi ma’lumotni o‘zgartirasiz?", reply_markup=edit_menu_kb())
    await cb.answer()

@dp.callback_query(F.data.startswith("edit:"))
async def edit_choose(cb: CallbackQuery):
    uid = cb.from_user.id
    u = get_user(uid)

    field = cb.data.split("edit:", 1)[1]

    if field == "full_name":
        user_stage[uid] = ST_FULLNAME
        await cb.message.answer("Ism-familiyangizni qayta yozing:")
    elif field == "xj_id":
        user_stage[uid] = ST_XJID
        await cb.message.answer("XJ ID ni qayta kiriting (7 xonali). Masalan: 0123456")
    elif field == "join":
        user_stage[uid] = ST_JOIN
        await cb.message.answer("XJ ga qachon qo‘shilgansiz? (masalan: 2024 oxiri)")
    elif field == "phone":
        user_stage[uid] = ST_PHONE
        await cb.message.answer("Telefon raqamingizni yuboring (kontakt):", reply_markup=contact_kb())
    elif field == "level":
        user_stage[uid] = ST_LEVEL
        await cb.message.answer("Darajangizni tanlang:", reply_markup=level_kb())
    else:
        await cb.message.answer("Noma’lum tanlov. /start dan qayta boshlang.")

    await cb.answer()

# ====== RUN ======
async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi. Railway Variables ga qo‘ying.")
        await init_db()

    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
# ============================
# STAGE 2 — Inline Material Menu
# ============================

ST_STAGE2 = "stage2_menu"
ST_STAGE3 = "stage3_tutorial"

def stage2_done_count(s2) -> int:
    return (
        int(s2["text_done"]) +
        int(s2["audio_done"]) +
        int(s2["video_done"]) +
        int(s2["links_done"])
    )

def stage2_intro_text(s2) -> str:
    return (
        "🔹 2-bosqich: XJ kompaniyasi bilan tanishib chiqish\n\n"
        "Quyidagi materiallarni ketma-ket ko‘rib chiqing.\n"
        "Hamma 4 tasi bajarilmaguncha “Davom etish” ochilmaydi.\n\n"
        f"🔒 Holat: {stage2_done_count(s2)} / 4 bajarildi"
    )

def stage2_kb(s2):
    def mark(x): return "✅" if x else "▫️"

    kb = InlineKeyboardBuilder()
    kb.button(text=f"{mark(s2['text_done'])} 📘 Matn", callback_data="s2:open:text")
    kb.button(text=f"{mark(s2['audio_done'])} 🎧 Audio", callback_data="s2:open:audio")
    kb.button(text=f"{mark(s2['video_done'])} 🎥 Video", callback_data="s2:open:video")
    kb.button(text=f"{mark(s2['links_done'])} 🔗 Linklar", callback_data="s2:open:links")
    kb.adjust(2, 2)

    all_done = (s2["text_done"] and s2["audio_done"] and s2["video_done"] and s2["links_done"])
    if all_done:
        kb.button(text="➡️ Davom etish", callback_data="s2:continue")
    else:
        kb.button(text="🔒 Davom etish", callback_data="s2:locked")
    kb.adjust(2, 2, 1)
    return kb.as_markup()

def one_confirm_kb(btn_text: str, cb_data: str):
    kb = InlineKeyboardBuilder()
    kb.button(text=btn_text, callback_data=cb_data)
    return kb.as_markup()

async def show_stage2(m: Message):
    # user stage2 ga o‘tdi deb DBga yozib qo‘yamiz (ixtiyoriy, lekin yaxshi)
    await upsert_user(m.from_user.id, stage=ST_STAGE2)

    s2 = await get_stage2(m.from_user.id)
    await m.answer(stage2_intro_text(s2), reply_markup=stage2_kb(s2))


# 1-bosqich yakunida shu chiqishi kerak:
@dp.message(F.text == "✅ Tasdiqlayman")
async def after_confirm_show_stage2(m: Message):
    await m.answer("Tabriklayman! Ro‘yxatdan muvaffaqiyatli o‘tdingiz ✅🎉\nKeyingi bosqichga o‘tamiz.")
    await show_stage2(m)


@dp.callback_query(F.data == "s2:locked")
async def s2_locked(cb: CallbackQuery):
    await cb.answer("Avval 4 ta materialni ham bajaring 🙂", show_alert=True)

@dp.callback_query(F.data == "s2:continue")
async def s2_continue(cb: CallbackQuery):
    await upsert_user(cb.from_user.id, stage=ST_STAGE3)
    await cb.message.answer("Zo‘r! ✅ 2-bosqich yakunlandi.\n\nEndi 3-bosqichga o‘tamiz 🎧 (keyingi qadamda qo‘shamiz).")
    await cb.answer()

@dp.callback_query(F.data.startswith("s2:open:"))
async def s2_open(cb: CallbackQuery):
    kind = cb.data.split(":")[-1]

    if kind == "text":
        await cb.message.answer(
            "📘 XJ kompaniyasi haqida matn\n\n"
            "XJ — bu zamonaviy biznes tizimi bo‘lib, hamkorlarga daromad topish, "
            "jamoa qurish va shaxsiy rivojlanish imkonini beradi.\n\n"
            "O‘qib bo‘lgach tasdiqlang:",
            reply_markup=one_confirm_kb("✅ O‘qidim", "s2:done:text")
        )

    elif kind == "audio":
        await cb.message.answer(
            "🎧 XJ haqida audio tushuntirish\n\n"
            "(Hozircha test matn. Keyin mp3 fayl qo‘shamiz.)\n\n"
            "Tugagach tasdiqlang:",
            reply_markup=one_confirm_kb("✅ Tingladim", "s2:done:audio")
        )

    elif kind == "video":
        await cb.message.answer(
            "🎥 XJ kompaniyasi haqida video\n\n"
            "(Hozircha video link qo‘ying.)\n\n"
            "Ko‘rib bo‘lgach tasdiqlang:",
            reply_markup=one_confirm_kb("✅ Ko‘rdim", "s2:done:video")
        )

    elif kind == "links":
        await cb.message.answer(
            "🔗 Foydali havolalar:\n"
            "1) Rasmiy sayt — https://...\n"
            "2) Telegram kanal — https://...\n"
            "3) Instagram — https://...\n\n"
            "Ko‘rib chiqqach tasdiqlang:",
            reply_markup=one_confirm_kb("✅ Ko‘rdim", "s2:done:links")
        )

    await cb.answer()

@dp.callback_query(F.data.startswith("s2:done:"))
async def s2_done(cb: CallbackQuery):
    kind = cb.data.split(":")[-1]
    field_map = {
        "text": "text_done",
        "audio": "audio_done",
        "video": "video_done",
        "links": "links_done",
    }
    field = field_map.get(kind)
    if not field:
        await cb.answer("Noto‘g‘ri amal", show_alert=True)
        return

    await set_stage2_done(cb.from_user.id, field)
    s2 = await get_stage2(cb.from_user.id)

    await cb.message.answer("✅ Bajarildi!\n\n" + stage2_intro_text(s2), reply_markup=stage2_kb(s2))
    await cb.answer()
