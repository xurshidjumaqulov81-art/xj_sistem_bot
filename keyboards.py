# keyboards.py
from aiogram.types import (
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def kb_start() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Start", callback_data="start:begin")
    return kb.as_markup()


def kb_contact() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="📱 Kontakt yuborish", request_contact=True))
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def kb_levels() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Oddiy", callback_data="reg:level:Oddiy")
    kb.button(text="Manager", callback_data="reg:level:Manager")
    kb.button(text="Bronza", callback_data="reg:level:Bronza")
    kb.button(text="Silver", callback_data="reg:level:Silver")
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
    kb.button(text="Qo‘shilgan vaqt", callback_data="reg:edit:join_date_text")
    kb.button(text="Telefon", callback_data="reg:edit:phone")
    kb.button(text="Daraja", callback_data="reg:edit:level")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def kb_done_button(text: str, callback_data: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=text, callback_data=callback_data)
    kb.adjust(1)
    return kb.as_markup()


def kb_material_menu(progress: dict) -> InlineKeyboardMarkup:
    # progress keys: matn_done, audio_done, video_done, links_done
    def mark(v: bool) -> str:
        return "✅" if v else "🔸"

    kb = InlineKeyboardBuilder()
    kb.button(text=f"{mark(progress.get('matn_done', False))} 📘 Matn", callback_data="m2:open:text")
    kb.button(text=f"{mark(progress.get('audio_done', False))} 🎧 Audio", callback_data="m2:open:audio")
    kb.button(text=f"{mark(progress.get('video_done', False))} 🎥 Video", callback_data="m2:open:video")
    kb.button(text=f"{mark(progress.get('links_done', False))} 🔗 Linklar", callback_data="m2:open:links")
    kb.adjust(2, 2)

    all_done = (
        progress.get("matn_done", False)
        and progress.get("audio_done", False)
        and progress.get("video_done", False)
        and progress.get("links_done", False)
    )

    if all_done:
        kb.button(text="➡️ Davom etish", callback_data="m2:continue")
    else:
        kb.button(text="🔒 Davom etish", callback_data="m2:locked")

    kb.adjust(2, 2, 1)
    return kb.as_markup()


def kb_tushundim_copy() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tushundim ✅ (Yuborish)", callback_data="s3:send_confirm")
    kb.adjust(1)
    return kb.as_markup()
