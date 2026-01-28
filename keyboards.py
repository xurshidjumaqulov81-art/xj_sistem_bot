# keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def kb_start() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Start", callback_data="start:begin")
    return kb.as_markup()

def kb_contact() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Kontakt yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def kb_levels() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for t in ["Oddiy", "Manager", "Bronza", "Silver"]:
        kb.button(text=t, callback_data=f"reg:level:{t}")
    kb.adjust(2, 2)
    return kb.as_markup()

def kb_confirm() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlayman", callback_data="reg:confirm:yes")
    kb.button(text="✏️ O‘zgartirmoqchiman", callback_data="reg:confirm:edit")
    kb.adjust(1, 1)
    return kb.as_markup()

def kb_edit_fields() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Ism-familiya", callback_data="reg:edit:full_name")
    kb.button(text="XJ ID", callback_data="reg:edit:xj_id")
    kb.button(text="Qo‘shilgan vaqt", callback_data="reg:edit:join_date")
    kb.button(text="Telefon", callback_data="reg:edit:phone")
    kb.button(text="Daraja", callback_data="reg:edit:level")
    kb.adjust(2, 2, 1)
    return kb.as_markup()

def kb_material_menu(progress: dict) -> InlineKeyboardMarkup:
    # progress: {"text":bool,"audio":bool,"video":bool,"links":bool}
    done = lambda x: "✅" if x else "🔸"
    kb = InlineKeyboardBuilder()
    kb.button(text=f"{done(progress.get('text'))} 📘 Matn", callback_data="m2:open:text")
    kb.button(text=f"{done(progress.get('audio'))} 🎧 Audio", callback_data="m2:open:audio")
    kb.button(text=f"{done(progress.get('video'))} 🎥 Video", callback_data="m2:open:video")
    kb.button(text=f"{done(progress.get('links'))} 🔗 Linklar", callback_data="m2:open:links")
    kb.adjust(2, 2)
    all_done = all(progress.get(k, False) for k in ["text", "audio", "video", "links"])
    if all_done:
        kb.button(text="➡️ Davom etish", callback_data="m2:continue")
    else:
        kb.button(text="🔒 Davom etish", callback_data="m2:locked")
    kb.adjust(2, 2, 1)
    return kb.as_markup()

def kb_done_button(text="✅ O‘qidim", cb="m2:done:text") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=text, callback_data=cb)
    return kb.as_markup()

def kb_stage3_help_copy() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tushundim ✅ (Yuborish)", callback_data="s3:copy_confirm")
    return kb.as_markup()

def kb_tingladim(cb: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tingladim", callback_data=cb)
    return kb.as_markup()

def kb_yes_no(prefix: str, idx: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Ha", callback_data=f"{prefix}:yes:{idx}")
    kb.button(text="❌ Yo‘q", callback_data=f"{prefix}:no:{idx}")
    kb.adjust(2)
    return kb.as_markup()

def kb_stage8_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📄 Yozma yo‘riqnoma", callback_data="s8:open:text")
    kb.button(text="🎥 Video qo‘llanma", callback_data="s8:open:video")
    kb.button(text="🔗 Havolalar", callback_data="s8:open:links")
    kb.button(text="➡️ 10-bosqichga o‘tish", callback_data="s8:continue")
    kb.adjust(1, 1, 1, 1)
    return kb.as_markup()

def kb_stage10_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔗 Taklif havolasi yuborish", callback_data="s10:ref")
    kb.button(text="📱 Kontaktni yuborish", callback_data="s10:contact")
    kb.button(text="❌ Hozircha yo‘q", callback_data="s10:none")
    kb.adjust(1, 1, 1)
    return kb.as_markup()
