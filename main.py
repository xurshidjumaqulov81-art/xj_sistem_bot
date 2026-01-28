import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import init_db, upsert_user, get_stage2, set_stage2_done

BOT_TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()

ST_STAGE2 = "stage2"
ST_STAGE3 = "stage3"


def stage2_done_count(s2):
    return sum([
        s2["text_done"],
        s2["audio_done"],
        s2["video_done"],
        s2["links_done"],
    ])


def stage2_text(s2):
    return (
        "🔹 *2-bosqich: XJ kompaniyasi bilan tanishish*\n\n"
        "Quyidagi 4 ta materialni ketma-ket ko‘rib chiqing.\n\n"
        f"📊 Holat: {stage2_done_count(s2)} / 4 bajarildi"
    )


def stage2_kb(s2):
    def mark(x): return "✅" if x else "▫️"

    kb = InlineKeyboardBuilder()
    kb.button(text=f"{mark(s2['text_done'])} 📘 Matn", callback_data="s2:text")
    kb.button(text=f"{mark(s2['audio_done'])} 🎧 Audio", callback_data="s2:audio")
    kb.button(text=f"{mark(s2['video_done'])} 🎥 Video", callback_data="s2:video")
    kb.button(text=f"{mark(s2['links_done'])} 🔗 Linklar", callback_data="s2:links")
    kb.adjust(2, 2)

    if all([
        s2["text_done"],
        s2["audio_done"],
        s2["video_done"],
        s2["links_done"],
    ]):
        kb.button(text="➡️ Davom etish", callback_data="s2:continue")
    else:
        kb.button(text="🔒 Davom etish", callback_data="s2:locked")

    kb.adjust(2, 2, 1)
    return kb.as_markup()


def confirm_kb(text, cb):
    kb = InlineKeyboardBuilder()
    kb.button(text=text, callback_data=cb)
    return kb.as_markup()


@dp.message(F.text == "/start")
async def start(m: Message):
    await upsert_user(m.from_user.id, ST_STAGE2)
    s2 = await get_stage2(m.from_user.id)
    await m.answer(stage2_text(s2), reply_markup=stage2_kb(s2), parse_mode="Markdown")


@dp.callback_query(F.data == "s2:locked")
async def locked(cb: CallbackQuery):
    await cb.answer("Avval 4 ta materialni tugating 🙂", show_alert=True)


@dp.callback_query(F.data == "s2:continue")
async def continue_stage(cb: CallbackQuery):
    await upsert_user(cb.from_user.id, ST_STAGE3)
    await cb.message.answer("🎉 2-bosqich yakunlandi!\nEndi 3-bosqichga o‘tamiz.")
    await cb.answer()


@dp.callback_query(F.data.startswith("s2:"))
async def open_material(cb: CallbackQuery):
    kind = cb.data.split(":")[1]

    texts = {
        "text": "📘 XJ kompaniyasi haqida MATN\n\n(O‘qib bo‘lgach tasdiqlang)",
        "audio": "🎧 XJ kompaniyasi haqida AUDIO\n\n(Tinglab bo‘lgach tasdiqlang)",
        "video": "🎥 XJ kompaniyasi haqida VIDEO\n\n(Ko‘rib bo‘lgach tasdiqlang)",
        "links": "🔗 Foydali havolalar\n\n(Kirib chiqqach tasdiqlang)",
    }

    await cb.message.answer(
        texts[kind],
        reply_markup=confirm_kb("✅ Bajarildi", f"s2done:{kind}")
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("s2done:"))
async def done(cb: CallbackQuery):
    kind = cb.data.split(":")[1]

    await set_stage2_done(cb.from_user.id, f"{kind}_done")
    s2 = await get_stage2(cb.from_user.id)

    await cb.message.answer(
        stage2_text(s2),
        reply_markup=stage2_kb(s2),
        parse_mode="Markdown"
    )
    await cb.answer()


async def main():
    await init_db()
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
