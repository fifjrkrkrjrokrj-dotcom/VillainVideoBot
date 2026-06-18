import logging
import config
import database as db
from utils import force_sub_keyboard, fmt_bold, fmt_code, fmt_blockquote

logger = logging.getLogger(__name__)


async def check_subscription(bot, user_id):
    sub = await db.get_subscription()
    if not sub or not sub.get("is_active"):
        return True

    channel_username = sub.get("channel_username")
    if not channel_username:
        return True

    try:
        member = await bot.get_chat_member(chat_id=channel_username, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning(f"Sub check failed for {user_id}: {e}")
        return False


def get_force_sub_message():
    return (
        "<blockquote>🔞 HOLD UP, YOU SEXY BEAST!</blockquote>\n\n"
        "Before I let you touch my naughty... ahem, <i>motivational</i> content,\n"
        "you need to join my <b>VIP CHANNEL</b> first. 😏\n\n"
        "✅ Join <b>5,000+</b> other horny go-getters\n"
        "✅ Get daily doses of 🔥 <b>FIRE</b> 🔥 content straight to your DMs\n"
        "✅ No spam. Just pure, unfiltered <i>pleasure</i>... of success\n\n"
        "<i>I'll know if you're lying... don't make me check 😉</i>"
    )


def get_sub_verified_message():
    return (
        "<blockquote>✅ OH YEAH... YOU'RE IN!</blockquote>\n\n"
        "Good boy/girl. You're officially a <b>VIP member</b> now.\n"
        "Use /start and I'll show you what's behind the curtain 😈🔥"
    )


def get_not_subscribed_message():
    return (
        "<blockquote>❌ NAH... YOU AIN'T IN YET</blockquote>\n\n"
        "Don't lie to me. Join the channel first,\n"
        "then tap <b>\"I'VE JOINED\"</b> like a good little slut. 😘"
    )
