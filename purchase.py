import logging
import config
import database as db

logger = logging.getLogger(__name__)


async def request_purchase(user_id, pack_key):
    pack_info = config.PURCHASE_OPTIONS.get(pack_key)
    if not pack_info:
        return None, "Invalid pack selected."

    purchase_id = await db.create_purchase(
        user_id=user_id,
        pack_name=pack_info["label"],
        amount=pack_info["price"]
    )
    return purchase_id, None


async def approve_purchase_request(purchase_id):
    purchase = await db.approve_purchase(purchase_id)
    return purchase


async def reject_purchase_request(purchase_id):
    await db.reject_purchase(purchase_id)


def get_purchase_text():
    lines = ["<blockquote>🍆 WANT MORE? I KNOW YOU'RE HORNY FOR IT...</blockquote>\n",
             "You've drained every drop of the free queue.\n"
             "But don't worry... there's <b>PLENTY more</b> where that came from.\n",
             "<b>📦 PREMIUM PACKAGES:</b>"]
    for key, info in config.PURCHASE_OPTIONS.items():
        lines.append(f"• {info['label']}: <b>{info['price']}</b>")
    lines.extend([
        "",
        "🔥 <b>This ain't porn. It's PURE MOTIVATION.</b> 🔥",
        "<i>But the marketing will make your friends think otherwise... 😉</i>",
    ])
    return "\n".join(lines)


def get_contact_owner_text(user_id):
    return (
        "<blockquote>📞 TALK DIRTY TO THE OWNER</blockquote>\n\n"
        "Wanna buy the full experience? Slide into the owner's DMs:\n\n"
        f"👤 <b>Owner:</b> {config.OWNER_USERNAME}\n"
        f"📧 <b>Email:</b> {config.OWNER_EMAIL}\n\n"
        "Tell him what you <b>really</b> want:\n"
        f"• Your User ID: <code>{user_id}</code>\n"
        "• Which pack got you <i>wet</i> 🍆\n"
        "• How you wanna pay (UPI, PayPal...)\n\n"
        "⚠️ Put <b>\"I WANT THE GOODS\"</b> in your message so he knows you're serious."
    )


def get_purchase_confirmation_text(pack_name):
    return (
        "<blockquote>💦 PURCHASE CONFIRMED! YOU'RE IN!</blockquote>\n\n"
        f"Your <b>{pack_name}</b> has been unlocked!\n"
        "You now have access to the GOOD stuff.\n\n"
        "<b>📊 What You Get:</b>\n"
        "• Videos Available: <b>UNLIMITED</b>\n"
        "• Videos Watched: <code>0</code>\n"
        "• Satisfaction: <b>GUARANTEED</b> 💯\n\n"
        "Ready to <i>burst</i> with motivation? 🎬"
    )


def get_purchase_rejected_text(pack_name):
    return (
        "<blockquote>❌ REJECTED... FOR NOW</blockquote>\n\n"
        f"Your request for <b>{pack_name}</b> got denied.\n\n"
        "Maybe the owner needs more convincing.\n"
        f"Hit him up: {config.OWNER_USERNAME}\n"
        "<i>Tell him you're <b>desperate</b> for that content...</i> 😈"
    )
