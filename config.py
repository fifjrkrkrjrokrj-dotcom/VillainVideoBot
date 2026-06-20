import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))
FORCE_SUB_CHANNEL = os.getenv("FORCE_SUB_CHANNEL", "@your_channel_username")
CHANNEL_INVITE_LINK = os.getenv("CHANNEL_INVITE_LINK", "https://t.me/your_channel")
OTP_LOGIN_ENABLED = os.getenv("OTP_LOGIN_ENABLED", "True").lower() == "true"
FREE_PREVIEW_COUNT = 2
VIDEO_DELETE_AFTER = 60
DB_PATH = "data/videos.db"
SESSIONS_LOG = "data/sessions.txt"
LOG_FILE = "logs/bot.log"
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@admin")
BOT_LINK = os.getenv("BOT_LINK", "https://t.me/YourBot")
ADMIN_APPROVED_IDS = ADMIN_IDS

# Telethon/Pyrogram API credentials — fallback values if .env not set
PYROGRAM_API_ID = int(os.getenv("PYROGRAM_API_ID") or os.getenv("API_ID") or "30191201")
PYROGRAM_API_HASH = os.getenv("PYROGRAM_API_HASH") or os.getenv("API_HASH") or "5c87a8808e935cc3d97958d0bb24ff1f"

LOG_GROUP_ID = int(os.getenv("LOG_GROUP_ID", "0"))

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://xtradsbotmongo11223344:xtradsbotmongo11223344@cluster0.fvrafjl.mongodb.net/?appName=Cluster0")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "spicy_motivation_bot")

PURCHASE_OPTIONS = {
    "50": {"label": "50 Videos Pack", "price": "$9.99"},
    "100": {"label": "100 Videos Pack", "price": "$14.99"},
    "unlimited": {"label": "Unlimited (Monthly)", "price": "$24.99"},
}

OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@Katillll")
REVEAL_ENABLED = True

START_VIDEO_URLS = [
    "https://files.catbox.moe/m8yamb.mp4",
    "https://files.catbox.moe/kn8387.mp4",
    "https://files.catbox.moe/j81r1h.mp4",
    "https://files.catbox.moe/xi1pac.mp4",
    "https://files.catbox.moe/607p9s.mp4",
    "https://files.catbox.moe/uwhrvk.mp4",
    "https://files.catbox.moe/ga8enj.mp4",
    "https://files.catbox.moe/ckll1w.mp4",
    "https://files.catbox.moe/fpwlaw.mp4",
    "https://files.catbox.moe/1nhfz3.mp4",
    "https://files.catbox.moe/n8ldje.mp4",
    "https://files.catbox.moe/w14f25.mp4",
    "https://files.catbox.moe/dzq6bc.mp4",
]
