import asyncio
import logging
import json
import os
import config
import database as db
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

TEMPLATES_FILE = "templates/broadcast_templates.json"

BROADCAST_KEYBOARDS = {
    "new_content": InlineKeyboardMarkup([
        [InlineKeyboardButton("💦 WATCH NOW", callback_data="next_video")],
        [InlineKeyboardButton("🍆 UPGRADE TO ACCESS", callback_data="purchase")],
        [InlineKeyboardButton("🔕 MUTE NOTIFICATIONS", callback_data="delete_session")],
    ]),
    "purchase_reminder": InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 CONTACT OWNER", callback_data="contact_owner")],
        [InlineKeyboardButton("🍑 WATCH FREE VIDEO", callback_data="main_menu")],
        [InlineKeyboardButton("❌ REMOVE ME", callback_data="delete_session")],
    ]),
    "referral": InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 SHARE BOT", callback_data="share_bot")],
        [InlineKeyboardButton("📊 MY REFERRALS", callback_data="stats")],
    ]),
    "inactive_users": InlineKeyboardMarkup([
        [InlineKeyboardButton("💪 BACK TO GRIND", callback_data="next_video")],
        [InlineKeyboardButton("😴 NOT NOW", callback_data="main_menu")],
    ]),
}


async def get_users_by_target(target):
    if target == "all":
        return await db.get_all_users()
    elif target == "active":
        return await db.get_active_users()
    elif target == "pending":
        return await db.get_users_by_status("pending")
    elif target == "purchased":
        return await db.get_purchased_users()
    return []


async def send_broadcast(bot, text, reply_markup=None, target="all", broadcast_id=None):
    users = await get_users_by_target(target)
    success = 0
    failed = 0
    total = len(users)

    for i, user in enumerate(users):
        try:
            await bot.send_message(
                chat_id=user["user_id"],
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            success += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Broadcast failed for {user['user_id']}: {e}")

        if i % 10 == 0 and broadcast_id:
            yield {"current": i + 1, "total": total, "success": success, "failed": failed}

        await asyncio.sleep(0.05)

    if broadcast_id:
        await db.create_broadcast(
            message=text[:500],
            media_type="text",
            target=target,
        )

    yield {"current": total, "total": total, "success": success, "failed": failed}


async def broadcast_template(bot, template_name, target="all"):
    templates = await load_templates()
    template = templates.get(template_name)
    if not template:
        return 0, 0

    text = template.get("text", "")
    target = target or template.get("target", "all")
    keyboard = BROADCAST_KEYBOARDS.get(template_name)

    async for progress in send_broadcast(bot, text, keyboard, target):
        pass

    return progress["success"], progress["failed"]


async def load_templates():
    try:
        if os.path.exists(TEMPLATES_FILE):
            with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load templates: {e}")
    return {}


async def save_template(name, text, target="all"):
    templates = await load_templates()
    templates[name] = {"name": name, "text": text, "target": target}
    os.makedirs(os.path.dirname(TEMPLATES_FILE), exist_ok=True)
    with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, indent=2, ensure_ascii=False)


def get_broadcast_keyboard(target):
    targets = {
        "all": "👥 All Users",
        "active": "✅ Active Users",
        "pending": "⏳ Pending Users",
        "purchased": "💰 Purchased Users",
    }
    label = targets.get(target, "👥 All Users")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🎯 Target: {label}", callback_data=f"bcast_target_{target}")],
        [InlineKeyboardButton("✅ CONFIRM SEND", callback_data="bcast_confirm")],
        [InlineKeyboardButton("❌ CANCEL", callback_data="bcast_cancel")],
    ])
