import random
import database as db
from utils import CATEGORIES, get_caption_for_category


async def get_video_for_user(user_id, category=None, only_free=False):
    user = await db.get_user(user_id)
    watched_ids = []

    if user and user["last_video_id"]:
        watched_ids.append(user["last_video_id"])

    if category:
        videos = await db.get_videos_by_category(category, limit=20, only_free=only_free)
    else:
        video = await db.get_random_video(exclude_ids=watched_ids if watched_ids else None, only_free=only_free)
        if not video:
            video = await db.get_random_video(only_free=only_free)
        return video

    if videos:
        return random.choice(videos)
    return await db.get_random_video(only_free=only_free)


def get_category_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = []
    for key, label in CATEGORIES:
        buttons.append(InlineKeyboardButton(label, callback_data=f"cat_{key}"))
    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(keyboard)
