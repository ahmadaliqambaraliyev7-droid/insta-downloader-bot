import os
import re
import tempfile
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from yt_dlp import YoutubeDL

TOKEN = os.getenv("BOT_TOKEN")

user_links = {}

def is_instagram_link(text):
    return "instagram.com" in text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Assalomu alaykum!\n\n"
        "📥 Instagram video yoki Reel linkini yuboring.\n"
        "Men sizga video yoki audio qilib yuklab beraman."
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not is_instagram_link(text):
        await update.message.reply_text("❌ Iltimos, Instagram link yuboring.")
        return

    user_links[update.effective_user.id] = text

    keyboard = [
        [
            InlineKeyboardButton("🎥 Video yuklash", callback_data="download_video"),
            InlineKeyboardButton("🎵 Audio MP3 yuklash", callback_data="download_audio"),
        ]
    ]

    await update.message.reply_text(
        "Qaysi formatda yuklab olay?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    url = user_links.get(user_id)

    if not url:
        await query.message.reply_text("❌ Link topilmadi. Qaytadan Instagram link yuboring.")
        return

    if query.data == "download_video":
        await query.message.reply_text("⏳ Video yuklanmoqda...")
        await download_video(query, url)

    elif query.data == "download_audio":
        await query.message.reply_text("⏳ Audio yuklanmoqda...")
        await download_audio(query, url)

async def download_video(query, url):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "outtmpl": f"{tmpdir}/video.%(ext)s",
                "format": "mp4/best",
                "noplaylist": True,
                "quiet": True,
            }

            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)

            files = list(Path(tmpdir).glob("*"))
            if files:
                file_path = str(files[0])

            with open(file_path, "rb") as video:
                await query.message.reply_video(video=video, caption="✅ Video tayyor")

    except Exception as e:
        await query.message.reply_text(f"❌ Video yuklanmadi.\nSabab: {e}")

async def download_audio(query, url):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "outtmpl": f"{tmpdir}/audio.%(ext)s",
                "format": "bestaudio/best",
                "noplaylist": True,
                "quiet": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }

            with YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)

            files = list(Path(tmpdir).glob("*.mp3"))

            if not files:
                await query.message.reply_text("❌ MP3 yaratilmadi. Serverda ffmpeg yo‘q bo‘lishi mumkin.")
                return

            with open(files[0], "rb") as audio:
                await query.message.reply_audio(audio=audio, caption="✅ Audio MP3 tayyor")

    except Exception as e:
        await query.message.reply_text(f"❌ Audio yuklanmadi.\nSabab: {e}")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(download_callback))

    app.run_polling()

if name == "__main__":
    main()
