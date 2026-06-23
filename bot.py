import os
import json
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
ADMIN_ID = 1133808611

DATA_FILE = "data.json"
user_links = {}


def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "users": [],
            "video_count": 0,
            "audio_count": 0,
            "total_links": 0
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except:
        return {
            "users": [],
            "video_count": 0,
            "audio_count": 0,
            "total_links": 0
        }


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


data = load_data()


def add_user(user_id):
    user_id = str(user_id)
    if user_id not in data["users"]:
        data["users"].append(user_id)
        save_data(data)


def is_admin(user_id):
    return user_id == ADMIN_ID


def is_instagram_link(text):
    return text and "instagram.com" in text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user.id)

    await update.message.reply_text(
        "👋 Assalomu alaykum!\n\n"
        "📥 Instagram video yoki Reel linkini yuboring.\n"
        "Men sizga video yoki audio qilib yuklab beraman."
    )


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    text = (
        "👑 ADMIN PANEL\n\n"
        f"👥 Foydalanuvchilar: {len(data['users'])}\n"
        f"🔗 Linklar: {data['total_links']}\n"
        f"🎥 Yuklangan videolar: {data['video_count']}\n"
        f"🎵 Yuklangan audiolar: {data['audio_count']}\n\n"
        "Komandalar:\n"
        "/stats - statistika\n"
        "/broadcast xabar - hammaga xabar yuborish"
    )

    await update.message.reply_text(text)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(
        "📊 STATISTIKA\n\n"
        f"👥 Foydalanuvchilar: {len(data['users'])}\n"
        f"🔗 Linklar: {data['total_links']}\n"
        f"🎥 Videolar: {data['video_count']}\n"
        f"🎵 Audiolar: {data['audio_count']}"
    )


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    message = " ".join(context.args)

    if not message:
        await update.message.reply_text(
            "❌ Xabar yozing.\n\nMasalan:\n/broadcast Salom hammaga!"
        )
        return

    sent = 0
    failed = 0

    await update.message.reply_text("📤 Xabar yuborish boshlandi...")

    for user_id in data["users"]:
        try:
            await context.bot.send_message(chat_id=int(user_id), text=message)
            sent += 1
        except:
            failed += 1

    await update.message.reply_text(
        f"✅ Yuborildi: {sent}\n"
        f"❌ Yuborilmadi: {failed}"
    )


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user.id)

    text = update.message.text.strip()

    if not is_instagram_link(text):
        await update.message.reply_text("❌ Iltimos, Instagram link yuboring.")
        return

    user_links[update.effective_user.id] = text
    data["total_links"] += 1
    save_data(data)

    keyboard = [
        [
            InlineKeyboardButton("🎥 Video yuklash", callback_data="download_video"),
            InlineKeyboardButton("🎵 Audio MP3 yuklash", callback_data="download_audio"),
        ]
    ]

    await update.message.reply_text(
        "Qaysi formatda yuklab olay?",
        reply_markup=InlineKeyboardMarkup(keyboard),
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
                "merge_output_format": "mp4",
            }

            with YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)

            files = list(Path(tmpdir).glob("*"))

            if not files:
                await query.message.reply_text("❌ Video topilmadi.")
                return

            file_path = str(files[0])

            with open(file_path, "rb") as video:
                await query.message.reply_video(video=video, caption="✅ Video tayyor")

            data["video_count"] += 1
            save_data(data)

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

            data["audio_count"] += 1
            save_data(data)

    except Exception as e:
        await query.message.reply_text(f"❌ Audio yuklanmadi.\nSabab: {e}")


def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN topilmadi. Railway Variables ichiga BOT_TOKEN qo‘shing.")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(download_callback))

    app.run_polling()


if __name__ == "__main__":
    main()
