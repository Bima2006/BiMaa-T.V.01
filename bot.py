# bot.py
import os
from pyrogram import Client, filters
from yt_dlp import YoutubeDL

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Client("downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

WELCOME_MSG = """
👋 හෙලෝ! මම ඔබේ Music & Video Downloader Bot - 🎵📽️

📥 Simply send me a YouTube/TikTok/Instagram video link and I’ll give you the download options!

🛠 Powered by BIMSARA 🔥
"""

@bot.on_message(filters.command("start"))
@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_photo(
        photo="https://github.com/Bima2006/BiMaa-T.V.01/blob/main/image_2025-06-02_091653343.png",
        caption="""
👑 *Welcome to BiMaa-T.V.01* 🎵📽️

🖼️ Powered by BIMSARA

📥 Simply send a YouTube, TikTok, or Instagram video link and I’ll give you download options in MP3 or MP4 format.

🚀 Let’s get downloading!
        """,
        parse_mode="markdown"
    )


@bot.on_message(filters.text & filters.private)
async def download_video(client, message):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.reply("කරුණාකර වලංගු වීඩියෝ ලින්ක් එකක් දෙන්න.")
        return

    msg = await message.reply("📥 Downloading... Please wait.")
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": "%(title)s.%(ext)s",
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_name = ydl.prepare_filename(info)

        await client.send_document(chat_id=message.chat.id, document=file_name)
        os.remove(file_name)
        await msg.delete()
    except Exception as e:
        await msg.edit(f"❌ Error: {e}")

bot.run()

