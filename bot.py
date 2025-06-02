import os
import json
import yt_dlp
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.error import TelegramError
from telegram.request import HTTPXRequest

# --- Configurations ---
BOT_TOKEN = "8060774807:AAGHHZr-ZOI4AKOLJlBz47KAaQGvG5KKP2U"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Load movies data
with open("movies.json", "r", encoding="utf-8") as f:
    movies_data = json.load(f)

# --- Helper functions ---
def find_movie(movie_name):
    for movie in movies_data:
        if movie["name"].lower() == movie_name.lower():
            return movie
    return None

async def fetch_video_info(url):
    def _fetch():
        ydl_opts = {'quiet': True, 'skip_download': True, 'noplaylist': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    return await asyncio.to_thread(_fetch)

async def download_audio(url):
    def _download():
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'audio.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return "audio.mp3"
    return await asyncio.to_thread(_download)

async def download_video(url, resolution):
    def _download():
        ydl_opts = {
            'format': f'bestvideo[height<={resolution}]+bestaudio/best/best',
            'outtmpl': 'video.%(ext)s',
            'merge_output_format': 'mp4',
            'quiet': True,
            'noplaylist': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        for f in os.listdir():
            if f.startswith("video.") and not f.endswith(".part"):
                return f
        return None
    return await asyncio.to_thread(_download)

# --- Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 හෙලෝ!\n\n"
        "ඔබට පහත විධාන භාවිතා කළ හැක:\n"
        "/downloadmp3 <YouTube link> - Audio download කරන්න\n"
        "/downloadvideo <YouTube link> - Video download කරන්න\n"
        "/search <movie name> - චිත්‍රපටයක් සෙවීමට\n\n"
        "🎬 ආරම්භ කරන්න!"
    )
    await update.message.reply_text(text)

async def downloadmp3_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ /downloadmp3 <YouTube link> කියලා type කරන්න.")
        return

    url = context.args[0]
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("⚠️ වැරදි YouTube ලින්ක් එකක්.")
        return

    try:
        info = await fetch_video_info(url)
    except Exception as e:
        await update.message.reply_text(f"❌ Video info error:\n{e}")
        return

    title = info.get("title", "Unknown")
    duration = info.get("duration", 0)
    duration_str = f"{duration//60}m {duration%60}s" if duration else "Unknown"
    thumbnail = info.get("thumbnail")

    caption = f"*{title}*\n⏰ දිනුම: {duration_str}\n\n🎵 MP3 එක download කිරීමට පටන් ගන්නවා."

    if thumbnail:
        await update.message.reply_photo(photo=thumbnail, caption=caption, parse_mode="Markdown")
    else:
        await update.message.reply_text(caption, parse_mode="Markdown")

    msg = await update.message.reply_text("🎧 MP3 එක download කරමින්...")

    try:
        audio_path = await download_audio(url)
    except Exception as e:
        await msg.edit_text("❌ Download error.")
        return

    try:
        await msg.edit_text("⬆️ Uploading...")
        with open(audio_path, "rb") as audio_file:
            await update.message.reply_audio(audio=audio_file)
        await msg.delete()
        await update.message.reply_text("✅ MP3 upload සාර්ථකයි!")
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

async def downloadvideo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ /downloadvideo <YouTube link> කියලා type කරන්න.")
        return

    url = context.args[0]
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("⚠️ වැරදි YouTube ලින්ක් එකක්.")
        return

    try:
        info = await fetch_video_info(url)
    except Exception as e:
        await update.message.reply_text(f"❌ Video info error:\n{e}")
        return

    title = info.get("title", "Unknown")
    duration = info.get("duration", 0)
    duration_str = f"{duration//60}m {duration%60}s" if duration else "Unknown"
    thumbnail = info.get("thumbnail")

    caption = f"*{title}*\n⏰ Duration: {duration_str}\n\n📺 Resolution එක තෝරන්න:"
    keyboard = [
        [InlineKeyboardButton("360p", callback_data=f"res_360|{url}"),
         InlineKeyboardButton("480p", callback_data=f"res_480|{url}")],
        [InlineKeyboardButton("720p", callback_data=f"res_720|{url}"),
         InlineKeyboardButton("1080p", callback_data=f"res_1080|{url}")]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    if thumbnail:
        await update.message.reply_photo(photo=thumbnail, caption=caption, parse_mode="Markdown", reply_markup=markup)
    else:
        await update.message.reply_text(text=caption, parse_mode="Markdown", reply_markup=markup)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ /search <movie name> ලෙස type කරන්න.")
        return

    movie_name = " ".join(context.args)
    movie = find_movie(movie_name)

    if movie:
        context.user_data["movie"] = movie
        message = (
            f"🎥 *චිත්‍රපට නම*: {movie['name']}\n"
            f"⭐️ *IMDb අගය*: {movie['imdb_rating']}\n"
            f"🎭 *කාණ්ඩය*: {movie['category']}\n"
            f"📝 *කෙටි විස්තරය*: {movie['short_review']}"
        )

        keyboard = [
            [InlineKeyboardButton("⬇️ Download Now", callback_data="download")],
            [InlineKeyboardButton("▶️ Watch Online", url=movie['video_link'])]
        ]
        markup = InlineKeyboardMarkup(keyboard)

        try:
            await update.message.reply_photo(photo=movie["image_url"], caption=message, reply_markup=markup, parse_mode="Markdown")
        except TelegramError:
            await update.message.reply_text(message, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ සමාවන්න, චිත්‍රපටය හමු නොවුණා.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    movie = context.user_data.get("movie")

    if data.startswith("res_"):
        res_part, url = data.split("|", 1)
        resolution = int(res_part.replace("res_", ""))

        status_msg = await context.bot.send_message(chat_id=query.message.chat_id, text=f"🎬 {resolution}p video එක download කරමින්...")

        try:
            video_path = await download_video(url, resolution)
            if not video_path:
                await status_msg.edit_text("❌ Video එක download කරන්න බැරි වුණා.")
                return
        except Exception as e:
            await status_msg.edit_text(f"❌ Error: {e}")
            return

        size = os.path.getsize(video_path)
        if size > MAX_FILE_SIZE:
            await status_msg.edit_text(f"❌ File size {size / (1024 * 1024):.2f}MB. 50MB වලට වැඩියි.")
            os.remove(video_path)
            return

        uploading_msg = await context.bot.send_message(chat_id=query.message.chat_id, text="⬆️ Uploading video...")
        await status_msg.delete()

        try:
            with open(video_path, 'rb') as video_file:
                await context.bot.send_video(chat_id=query.message.chat_id, video=video_file, supports_streaming=True)
            await uploading_msg.delete()
            await context.bot.send_message(chat_id=query.message.chat_id, text="✅ Video upload සාර්ථකයි!")
        finally:
            if os.path.exists(video_path):
                os.remove(video_path)

    elif data == "download":
        if movie and "qualities" in movie:
            quality_buttons = []
            if isinstance(movie["qualities"], dict):
                for q in movie["qualities"]:
                    label = q  # e.g. "360p"
                    callback_quality = q.replace("p", "")  # "360"
                    quality_buttons.append([InlineKeyboardButton(label, callback_data=f"quality_{callback_quality}")])
            # Back button
            quality_buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_movie")])
            await query.edit_message_reply_markup(InlineKeyboardMarkup(quality_buttons))
        else:
            await query.edit_message_text("⚠️ Download options නොමැත.")

    elif data.startswith("quality_"):
        quality = data.split("_")[1]
        download_link = None

        if movie and "qualities" in movie and isinstance(movie["qualities"], dict):
            key = quality + "p"
            if key in movie["qualities"]:
                download_link = movie["qualities"][key]

        if download_link:
            keyboard = [
                [InlineKeyboardButton(f"Open {quality}p Link", url=download_link)],
                [InlineKeyboardButton("⬅️ Back", callback_data="download")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"⬇️ *{quality}p* link එක පහතින් Open කරන්න.",
                parse_mode="Markdown",
                reply_markup=markup
            )
        else:
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"⚠️ Link එක හමු නොවුණා. (quality: {quality})")

async def handle_fallback_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ කරුණාකර /downloadmp3, /downloadvideo හෝ /search <name> ලෙස විධානයක් භාවිතා කරන්න.")

# --- Main ---
if __name__ == '__main__':
    request = HTTPXRequest(http_version="1.1")
    app = Application.builder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("downloadmp3", downloadmp3_command))
    app.add_handler(CommandHandler("downloadvideo", downloadvideo_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_fallback_message))

    print("✅ Bot is running...")
    app.run_polling()

bot.run()

