# keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def kb_start() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="▶️ Бошлаш", callback_data="start:begin")
    return kb.as_markup()


def kb_contact() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Контакт юбориш", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def kb_levels() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⭐ 1-даража", callback_data="reg:level:1")
    kb.button(text="⭐ 2-даража", callback_data="reg:level:2")
    kb.button(text="⭐ 3-даража", callback_data="reg:level:3")
    kb.adjust(1)
    return kb.as_markup()


def kb_confirm() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Тасдиқлайман", callback_data="reg:confirm:yes")
    kb.button(text="✏️ Ўзгартириш", callback_data="reg:confirm:edit")
    kb.adjust(2)
    return kb.as_markup()


def kb_edit_fields() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Исм", callback_data="edit:full_name")
    kb.button(text="🆔 XJ ID", callback_data="edit:xj_id")
    kb.button(text="📅 Қўшилган вақт", callback_data="edit:join_date_text")
    kb.button(text="📞 Телефон", callback_data="edit:phone")
    kb.button(text="⭐ Даража", callback_data="edit:level")
    kb.adjust(2)
    return kb.as_markup()


def _status(progress: dict, key: str) -> str:
    return "✅" if progress.get(key) else "◻️"


def _remaining_text(progress: dict) -> str:
    missing = []
    if not progress.get("matn_done"):
        missing.append("📘 Матн")
    if not progress.get("audio_done"):
        missing.append("🎧 Аудио")
    if not progress.get("video_done"):
        missing.append("🎥 Видео")
    if not progress.get("links_done"):
        missing.append("🔗 Линклар")
    if not missing:
        return "✅ Ҳаммаси тайёр!"
    return "Қолгани: " + ", ".join(missing)


def kb_material_menu(progress: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    kb.button(text=f"{_status(progress,'matn_done')} 📘 Матн", callback_data="m2:open:text")
    kb.button(text=f"{_status(progress,'audio_done')} 🎧 Аудио", callback_data="m2:open:audio")
    kb.button(text=f"{_status(progress,'video_done')} 🎥 Видео", callback_data="m2:open:video")
    kb.button(text=f"{_status(progress,'links_done')} 🔗 Линклар", callback_data="m2:open:links")
    kb.adjust(2)

    all_done = all([
        progress.get("matn_done"),
        progress.get("audio_done"),
        progress.get("video_done"),
        progress.get("links_done"),
    ])

    if all_done:
        kb.button(text="➡️ Давом этиш", callback_data="m2:continue")
    else:
        kb.button(text="🔒 Давом этиш", callback_data="m2:locked")

    kb.adjust(2, 2, 1)
    return kb.as_markup()


def kb_done_button(text: str, cb: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=text, callback_data=cb)
    return kb.as_markup()


def kb_stage3_start() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Бошлаймиз", callback_data="s3:start")
    return kb.as_markup()
