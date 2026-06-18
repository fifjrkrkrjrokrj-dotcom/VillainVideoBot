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

PYROGRAM_API_ID = int(os.getenv("PYROGRAM_API_ID", "0"))
PYROGRAM_API_HASH = os.getenv("PYROGRAM_API_HASH", "")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "spicy_motivation_bot")

PURCHASE_OPTIONS = {
    "50": {"label": "50 Videos Pack", "price": "$9.99"},
    "100": {"label": "100 Videos Pack", "price": "$14.99"},
    "unlimited": {"label": "Unlimited (Monthly)", "price": "$24.99"},
}

OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@YourOwnerUsername")
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "owner@example.com")
REVEAL_ENABLED = True
