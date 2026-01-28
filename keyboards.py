# keyboards.py
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def kb_start() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Старт", callback_data="start:begin")
    return kb.as_markup()


def kb_contact() -> ReplyKeyboardMarkup:
    # Contact so‘rash tugmasi
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Контакт юбориш", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def kb_levels() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Оддий", callback_data="reg:level:oddiy")
    kb.button(text="Manager", callback_data="reg:level:manager")
    kb.button(text="Bronza", callback_data="reg:level:bronza")
    kb.button(text="Silver", callback_data="reg:level:silver")
    kb.adjust(2)
    return kb.as_markup()


def kb_confirm() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Тасдиқлайман", callback_data="reg:confirm:yes")
    kb.button(text="✏️ Ўзгартирмоқчиман", callback_data="reg:confirm:edit")
    kb.adjust(1)
    return kb.as_markup()


def kb_edit_fields() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Исм-фамилия", callback_data="reg:edit:full_name")
    kb.button(text="XJ ID", callback_data="reg:edit:xj_id")
    kb.button(text="Қўшилган вақт", callback_data="reg:edit:join_date_text")
    kb.button(text="Телефон", callback_data="reg:edit:phone")
    kb.button(text="Даража", callback_data="reg:edit:level")
    kb.adjust(2)
    return kb.as_markup()


def kb_done_button(text: str, cb: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=text, callback_data=cb)
    return kb.as_markup()


def kb_material_menu(progress: dict) -> InlineKeyboardMarkup:
    # progress keys: matn_done, audio_done, video_done, links_done
    matn = "✅ 📘 Матн" if progress.get("matn_done") else "📘 Матн"
    audio = "✅ 🎧 Аудио" if progress.get("audio_done") else "🎧 Аудио"
    video = "✅ 🎥 Видео" if progress.get("video_done") else "🎥 Видео"
    links = "✅ 🔗 Линклар" if progress.get("links_done") else "🔗 Линклар"

    done_count = sum([
        1 if progress.get("matn_done") else 0,
        1 if progress.get("audio_done") else 0,
        1 if progress.get("video_done") else 0,
        1 if progress.get("links_done") else 0,
    ])

    missing = []
    if not progress.get("matn_done"):
        missing.append("Матн")
    if not progress.get("audio_done"):
        missing.append("Аудио")
    if not progress.get("video_done"):
        missing.append("Видео")
    if not progress.get("links_done"):
        missing.append("Линклар")

    if missing:
        status_text = f"🔒 Ҳолат: {done_count}/4\nҚолганлар: " + ", ".join(missing)
    else:
        status_text = "🎉 Ҳолат: 4/4 — тайёр!"

    kb = InlineKeyboardBuilder()
    kb.button(text=matn, callback_data="m2:open:text")
    kb.button(text=audio, callback_data="m2:open:audio")
    kb.button(text=video, callback_data="m2:open:video")
    kb.button(text=links, callback_data="m2:open:links")
    kb.adjust(2)

    # status line
    kb.row(InlineKeyboardButton(text=status_text, callback_data="noop"))

    # continue
    if done_count == 4:
        kb.row(InlineKeyboardButton(text="➡️ Давом этиш", callback_data="m2:continue"))
    else:
        kb.row(InlineKeyboardButton(text="🔒 Давом этиш", callback_data="m2:continue_locked"))

    return kb.as_markup()
