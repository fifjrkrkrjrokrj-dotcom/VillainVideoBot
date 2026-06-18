import asyncio
import logging
import random
from pyrogram import Client
import config

logger = logging.getLogger(__name__)

otp_storage = {}
twofa_storage = {}
login_attempts = {}


async def send_otp_pyrogram(phone_number):
    if not config.PYROGRAM_API_ID or not config.PYROGRAM_API_HASH:
        return None

    try:
        app = Client(
            "bot_login_session",
            api_id=config.PYROGRAM_API_ID,
            api_hash=config.PYROGRAM_API_HASH,
            in_memory=True
        )
        await app.start()

        sent = await app.send_code(phone_number)
        phone_code_hash = sent.phone_code_hash

        await app.stop()
        return {"phone_code_hash": phone_code_hash, "phone_number": phone_number}
    except Exception as e:
        logger.error(f"Pyrogram send_code failed: {e}")
        return None


async def verify_otp_pyrogram(phone_number, phone_code_hash, otp):
    if not config.PYROGRAM_API_ID or not config.PYROGRAM_API_HASH:
        return None

    try:
        app = Client(
            "bot_login_verify",
            api_id=config.PYROGRAM_API_ID,
            api_hash=config.PYROGRAM_API_HASH,
            in_memory=True
        )
        await app.start()

        try:
            signed_in = await app.sign_in(phone_number, phone_code_hash, otp)
            if hasattr(signed_in, 'id'):
                user_id = signed_in.id
                await app.stop()
                return {"user_id": user_id, "twofa": False}
        except Exception as e:
            error_str = str(e)
            if "PHONE_CODE_INVALID" in error_str:
                await app.stop()
                return {"error": "invalid_otp"}
            elif "SESSION_PASSWORD_NEEDED" in error_str:
                await app.stop()
                return {"error": "2fa_required", "phone_number": phone_number}

        await app.stop()
        return {"error": "unknown"}
    except Exception as e:
        logger.error(f"Pyrogram verify_otp failed: {e}")
        return {"error": "pyrogram_error"}


async def check_2fa_password(phone_number, password):
    if not config.PYROGRAM_API_ID or not config.PYROGRAM_API_HASH:
        return None

    try:
        app = Client(
            "bot_login_2fa",
            api_id=config.PYROGRAM_API_ID,
            api_hash=config.PYROGRAM_API_HASH,
            in_memory=True
        )
        await app.start()

        try:
            await app.check_password(password)
            await app.stop()
            return {"success": True}
        except Exception as e:
            await app.stop()
            if "PASSWORD_HASH_INVALID" in str(e):
                return {"error": "invalid_password"}
            return {"error": str(e)}
    except Exception as e:
        logger.error(f"Pyrogram 2FA failed: {e}")
        return {"error": "pyrogram_error"}


def generate_mock_otp():
    return str(random.randint(10000, 99999))


def get_otp_attempts(user_id):
    return login_attempts.get(user_id, {"otp": 0, "2fa": 0})


def increment_otp_attempts(user_id):
    attempts = login_attempts.setdefault(user_id, {"otp": 0, "2fa": 0})
    attempts["otp"] += 1
    return attempts["otp"]


def increment_2fa_attempts(user_id):
    attempts = login_attempts.setdefault(user_id, {"otp": 0, "2fa": 0})
    attempts["2fa"] += 1
    return attempts["2fa"]


def reset_attempts(user_id):
    login_attempts.pop(user_id, None)
