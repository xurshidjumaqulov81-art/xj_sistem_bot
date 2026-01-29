# keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def kb_start():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Бошлаш", callback_data="start:begin")
    return kb.as_markup()

def kb_contact():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Контакт юбориш", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def kb_levels():
    kb = InlineKeyboardBuilder()
    for lvl in ["Oddiy Xamkor", "XJ Manager", "XJ Bronze", "XJ Silver"]:
        kb.button(text=lvl, callback_data=f"reg:level:{lvl}")
    kb.adjust(2)
    return kb.as_markup()

def kb_confirm():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Ҳа, тасдиқлайман", callback_data="reg:confirm:yes")
    kb.button(text="✏️ Таҳрирлаш", callback_data="reg:confirm:edit")
    kb.adjust(1)
    return kb.as_markup()

def kb_edit_fields():
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Исм", callback_data="edit:full_name")
    kb.button(text="🆔 XJ ID", callback_data="edit:xj_id")
    kb.button(text="📅 Қўшилган вақт", callback_data="edit:join_date_text")
    kb.button(text="📞 Телефон", callback_data="edit:phone")
    kb.button(text="⭐ Даража", callback_data="edit:level")
    kb.adjust(2)
    return kb.as_markup()

def _status(done: bool) -> str:
    return "✅" if done else "⬜️"

def kb_material_menu(progress: dict):
    # progress keys: text_done, audio_done, video_done, links_done
    kb = InlineKeyboardBuilder()
    kb.button(text=f"{_status(progress['text_done'])} 📘 Матн", callback_data="m2:open:text")
    kb.button(text=f"{_status(progress['audio_done'])} 🎧 Аудио", callback_data="m2:open:audio")
    kb.button(text=f"{_status(progress['video_done'])} 🎥 Видео", callback_data="m2:open:video")
    kb.button(text=f"{_status(progress['links_done'])} 🔗 Линклар", callback_data="m2:open:links")
    kb.adjust(2)

    all_done = progress["text_done"] and progress["audio_done"] and progress["video_done"] and progress["links_done"]
    if all_done:
        kb.button(text="➡️ Давом этиш", callback_data="m2:continue")
    else:
        kb.button(text="🔒 Давом этиш", callback_data="m2:continue_locked")
    kb.adjust(2, 2, 1)
    return kb.as_markup()

def kb_done_button(text: str, cb: str):
    kb = InlineKeyboardBuilder()
    kb.button(text=text, callback_data=cb)
    return kb.as_markup()

def kb_stage3_start():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Бошлаймиз", callback_data="s3:start")
    return kb.as_markup()
