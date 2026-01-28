# main.py (PART 1/6)
import asyncio
import re
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart

from config import BOT_TOKEN, ADMIN_IDS
import db

from keyboards import (
    kb_start, kb_contact, kb_levels, kb_confirm, kb_edit_fields,
    kb_material_menu, kb_done_button, kb_stage3_help_copy, kb_tingladim,
    kb_yes_no, kb_stage8_menu, kb_stage10_menu
)

# === STATES ===
REG_NAME = "REG_NAME"
REG_XJ_ID = "REG_XJ_ID"
REG_JOIN_DATE = "REG_JOIN_DATE"
REG_PHONE = "REG_PHONE"
REG_LEVEL = "REG_LEVEL"
REG_CONFIRM = "REG_CONFIRM"
REG_EDIT_MENU = "REG_EDIT_MENU"

MATERIAL_MENU = "MATERIAL_MENU"

STAGE3_TUTORIAL = "STAGE3_TUTORIAL"

STAGE4_INTRO_AUDIO = "STAGE4_INTRO_AUDIO"
STAGE4_COLLECT = "STAGE4_COLLECT"  # index saqlanadi db'da yoki user_state

STAGE5_AUDIO_REQUIRED = "STAGE5_AUDIO_REQUIRED"
STAGE5_COLLECT = "STAGE5_COLLECT"

STAGE6_AUDIO_REQUIRED = "STAGE6_AUDIO_REQUIRED"
STAGE6_COLLECT = "STAGE6_COLLECT"

STAGE7_AUDIO_REQUIRED = "STAGE7_AUDIO_REQUIRED"
STAGE7_CHECK = "STAGE7_CHECK"
STAGE7_TEXT = "STAGE7_TEXT"

STAGE8_AUDIO_REQUIRED = "STAGE8_AUDIO_REQUIRED"
STAGE8_MENU = "STAGE8_MENU"

STAGE10_INTRO = "STAGE10_INTRO"
STAGE10_WAIT_CONTACT = "STAGE10_WAIT_CONTACT"

CONFIRM_EXACT = "Tushundim ✅"

bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def safe_answer_cb(call: CallbackQuery):
    try:
        await call.answer()
    except:
        pass

async def send_to_admins(text: str):
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, text)
        except:
            pass

def _clean(s: str) -> str:
    return (s or "").strip()

def _xj_id_ok(s: str) -> bool:
    return bool(re.fullmatch(r"\d{7}", s.strip()))

async def goto_state(user_id: int, state: str):
    await db.set_state(user_id, state)

async def get_state(user_id: int) -> str:
    st = await db.get_state(user_id)
    return st or REG_NAME

# ----- START -----
@dp.message(CommandStart())
async def cmd_start(msg: Message):
    user_id = msg.from_user.id

    # referral: /start ref_ABC123
    payload = (msg.text or "").split(maxsplit=1)
    start_param = payload[1].strip() if len(payload) > 1 else ""
    inviter_id = None
    if start_param.startswith("ref_"):
        # db’da ref_code bo‘yicha inviter topish
        inviter_id = await db.get_user_id_by_ref_code(start_param.replace("ref_", "", 1))

    u = await db.get_user(user_id)
    if not u:
        await db.upsert_user(user_id=user_id, inviter_id=inviter_id)
        await goto_state(user_id, REG_NAME)

    text = (
        "XJ rasmiy bot tizimiga xush kelibsiz!\n\n"
        "Bu yerda siz ro‘yxatdan o‘tasiz, materiallarni olasiz va ishni bosqichma-bosqich boshlaysiz.\n\n"
        "Boshlashga tayyor bo‘lsangiz, pastdagi tugmani bosing."
    )
    await msg.answer(text, reply_markup=kb_start())

@dp.callback_query(F.data == "start:begin")
async def start_begin(call: CallbackQuery):
    await safe_answer_cb(call)
    user_id = call.from_user.id
    await goto_state(user_id, REG_NAME)
    await call.message.answer("Ro‘yxatdan o‘tishni boshlaymiz ✅\nIltimos, ism-familiyangizni yozing.")

# ========== Dispatcher for text messages by state ==========
@dp.message(F.text)
async def on_text(msg: Message):
    user_id = msg.from_user.id
    st = await get_state(user_id)
    text = _clean(msg.text)

    if st == REG_NAME:
        if len(text) < 3:
            return await msg.answer("Iltimos, ism-familiyani to‘liqroq yozing.")
        await db.upsert_user(user_id=user_id, full_name=text)
        await goto_state(user_id, REG_XJ_ID)
        return await msg.answer("Rahmat ✅\nEndi XJ ID ni kiriting (7 xonali raqam).\nMasalan: 0123456")

    if st == REG_XJ_ID:
        if not _xj_id_ok(text):
            return await msg.answer("XJ ID 7 xonali bo‘lishi kerak.\nMasalan: 0123456")
        await db.upsert_user(user_id=user_id, xj_id=text)
        await goto_state(user_id, REG_JOIN_DATE)
        return await msg.answer(
            "Qabul qilindi ✅\nEndi: XJ ga qachon qo‘shilgansiz?\n"
            "Aniq sana bo‘lsa: YYYY-MM-DD\nYo‘q bo‘lsa taxminiy yozing (masalan: 2024 oxiri)."
        )

    if st == REG_JOIN_DATE:
        await db.upsert_user(user_id=user_id, join_date_text=text)
        await goto_state(user_id, REG_PHONE)
        return await msg.answer("Tushunarli ✅\nEndi telefon raqamingizni yuboring.\nPastdagi tugma orqali kontakt ulashing.", reply_markup=kb_contact())

    if st == STAGE3_TUTORIAL:
        # exact confirm
        if text == CONFIRM_EXACT:
            await db.mark_stage3_confirmed(user_id=user_id, confirmed_text=text)
            await msg.answer("Zo‘r! ✅ Darslik tasdiqlandi.\nEndi 4-bosqichga o‘tamiz: 20 ta odam ro‘yxati.")
            await goto_state(user_id, STAGE4_INTRO_AUDIO)
            return await msg.answer("Avval qisqa yo‘riqnomani tinglab oling 👇", reply_markup=kb_tingladim("s4:audio_done"))
        else:
            attempts = await db.inc_stage3_attempt(user_id=user_id)
            if attempts >= 3:
                return await msg.answer(
                    f"Iltimos, aynan shu ko‘rinishda yozing: <b>{CONFIRM_EXACT}</b>\n"
                    "Quyidagi tugmani bosib yuborsangiz ham bo‘ladi 👇",
                    reply_markup=kb_stage3_help_copy()
                )
            return await msg.answer(f"Iltimos, aynan shu ko‘rinishda yozing: <b>{CONFIRM_EXACT}</b>\n({attempts}/3 urinish)")

    # 4-bosqich 20 ta lead yig‘ish
    if st == STAGE4_COLLECT:
        idx = await db.get_stage4_index(user_id=user_id)  # 1..20
        if not text:
            return await msg.answer("Iltimos kamida bitta ism yozing.")
        await db.save_lead(user_id=user_id, index=idx, name_raw=text)
        if idx >= 20:
            await goto_state(user_id, STAGE5_AUDIO_REQUIRED)
            await msg.answer("Saqlandi ✅ (20/20) 🎉\nRo‘yxat tayyor!\nEndi 5-bosqichga o‘tamiz.")
            return await msg.answer("Avval yo‘riqnomani tinglang 👇", reply_markup=kb_tingladim("s5:audio_done"))
        else:
            await db.set_stage4_index(user_id=user_id, index=idx+1)
            return await msg.answer(f"Saqlandi ✅ ({idx}/20)\n{idx+1}/20 — Yana kim?")

    # 5-bosqich meeting status matn
    if st == STAGE5_COLLECT:
        idx = await db.get_stage5_index(user_id=user_id)
        if not text:
            return await msg.answer("Bo‘sh yubormang. Qisqa yozing (masalan: Ha, ertaga 18:00).")
        if len(text) > 300:
            return await msg.answer("Javob juda uzun. 300 belgidan kam qiling.")
        await db.save_meeting_note(user_id=user_id, index=idx, text=text)

        leads = await db.get_leads(user_id=user_id)
        if idx >= 20:
            await goto_state(user_id, STAGE6_AUDIO_REQUIRED)
            await msg.answer("Yozib olindi ✅ (20/20) 🎉\n5-bosqich yakunlandi.\nEndi 6-bosqich: Prezentatsiya.")
            return await msg.answer("Avval prezentatsiya yo‘riqnomasi audio 👇", reply_markup=kb_tingladim("s6:audio_done"))
        else:
            await db.set_stage5_index(user_id=user_id, index=idx+1)
            next_name = leads[idx]["name_raw"] if len(leads) > idx else f"{idx+1}-odam"
            return await msg.answer(f"Yozib olindi ✅ ({idx}/20)\n{idx+1}/20 — ({next_name})\nUchrashuv belgiladingizmi? Qisqa yozing.")

    # 7-bosqich: savol matnini qabul qilish (faqat Ha bosilgandan keyin)
    if st == STAGE7_TEXT:
        idx = await db.get_stage7_pending_index(user_id=user_id)
        if not text:
            return await msg.answer("Iltimos, savol matnini yozing.")
        qid = await db.save_followup_question(user_id=user_id, index=idx, question_text=text)
        await send_to_admins(f"❓ Follow-up savol\nUser: {user_id}\nLead index: {idx}\nSavol ID: {qid}\nSavol: {text}")
        await msg.answer("Rahmat ✅ Savol adminga yuborildi.\nJavob tayyor bo‘lsa shu bot orqali keladi.")

        # davom: keyingi idx
        await db.advance_stage7(user_id=user_id)  # next idx or finish
        nxt = await db.get_stage7_index(user_id=user_id)
        if nxt > 20:
            await goto_state(user_id, STAGE8_AUDIO_REQUIRED)
            return await msg.answer("7-bosqich yakunlandi 🎉\nEndi 8-bosqich: Xarid jarayoni.\nAvval audio 👇", reply_markup=kb_tingladim("s8:audio_done"))
        leads = await db.get_leads(user_id=user_id)
        name = leads[nxt-1]["name_raw"] if len(leads) >= nxt else f"{nxt}-odam"
        await goto_state(user_id, STAGE7_CHECK)
        return await msg.answer(f"{nxt}/20 — ({name})\nU siz javob berolmaydigan savol berdimi?", reply_markup=kb_yes_no("s7q", nxt))

    # 10-bosqich kontakt kutish
    if st == STAGE10_WAIT_CONTACT:
        return await msg.answer("Kontaktni pastdagi tugma bilan yuboring (📱 Kontakt yuborish).")

    # default
    await msg.answer("Tushunmadim. Pastdagi tugmalar orqali davom eting yoki /start bosing.")
