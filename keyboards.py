from aiogram.utils.keyboard import InlineKeyboardBuilder

def kb_material_menu(progress: dict):
    def mark(v: bool):
        return "✅" if v else "🔸"

    kb = InlineKeyboardBuilder()
    kb.button(text=f"{mark(progress.get('matn_done', False))} 📘 Matn", callback_data="m2:open:text")
    kb.button(text=f"{mark(progress.get('audio_done', False))} 🎧 Audio", callback_data="m2:open:audio")
    kb.button(text=f"{mark(progress.get('video_done', False))} 🎥 Video", callback_data="m2:open:video")
    kb.button(text=f"{mark(progress.get('links_done', False))} 🔗 Linklar", callback_data="m2:open:links")
    kb.adjust(2, 2)

    all_done = (
        progress.get("matn_done", False) and
        progress.get("audio_done", False) and
        progress.get("video_done", False) and
        progress.get("links_done", False)
    )

    if all_done:
        kb.button(text="➡️ Davom etish", callback_data="m2:continue")
    else:
        kb.button(text="🔒 Davom etish", callback_data="m2:locked")

    kb.adjust(2, 2, 1)
    return kb.as_markup()
