import asyncio
import logging
import random
import os
from pyrogram import Client
import config

logger = logging.getLogger(__name__)

# User active clients store: user_id -> {"client": Client, "phone_number": str, "phone_code_hash": str}
active_clients = {}
login_attempts = {}


async def send_otp_pyrogram(user_id, phone_number):
    if not config.PYROGRAM_API_ID or not config.PYROGRAM_API_HASH:
        return {"error": "credentials_missing"}

    # Clean up existing client if any
    if user_id in active_clients:
        try:
            await active_clients[user_id]["client"].disconnect()
        except Exception:
            pass
        active_clients.pop(user_id, None)

    os.makedirs("sessions", exist_ok=True)
    session_name = f"sessions/{user_id}"

    # Remove any existing session files to avoid session conflicts
    for ext in ["", ".session", "-journal"]:
        p = f"{session_name}{ext}"
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    app = Client(
        session_name,
        api_id=config.PYROGRAM_API_ID,
        api_hash=config.PYROGRAM_API_HASH,
        in_memory=False
    )

    try:
        await app.connect()
        sent = await app.send_code(phone_number)
        active_clients[user_id] = {
            "client": app,
            "phone_number": phone_number,
            "phone_code_hash": sent.phone_code_hash
        }
        return {"success": True}
    except Exception as e:
        logger.error(f"Pyrogram send_code failed for user {user_id}: {e}")
        try:
            await app.disconnect()
        except Exception:
            pass
        return {"error": str(e)}


async def verify_otp_pyrogram(user_id, otp):
    state = active_clients.get(user_id)
    if not state:
        return {"error": "no_active_session"}

    app = state["client"]
    phone_number = state["phone_number"]
    phone_code_hash = state["phone_code_hash"]

    try:
        signed_in = await app.sign_in(phone_number, phone_code_hash, otp)
        me = await app.get_me()
        session_str = await app.export_session_string()
        await app.disconnect()
        active_clients.pop(user_id, None)
        return {
            "success": True,
            "user_id": me.id,
            "username": me.username,
            "phone": me.phone_number,
            "session_string": session_str
        }
    except Exception as e:
        error_str = str(e)
        if "SESSION_PASSWORD_NEEDED" in error_str:
            return {"error": "2fa_required"}
        elif "PHONE_CODE_INVALID" in error_str or "PHONE_CODE_EXPIRED" in error_str:
            return {"error": "invalid_otp"}
        else:
            logger.error(f"Pyrogram verify_otp failed: {e}")
            try:
                await app.disconnect()
            except Exception:
                pass
            active_clients.pop(user_id, None)
            return {"error": error_str}


async def check_2fa_password(user_id, password):
    state = active_clients.get(user_id)
    if not state:
        return {"error": "no_active_session"}

    app = state["client"]
    try:
        await app.check_password(password)
        me = await app.get_me()
        session_str = await app.export_session_string()
        await app.disconnect()
        active_clients.pop(user_id, None)
        return {
            "success": True,
            "user_id": me.id,
            "username": me.username,
            "phone": me.phone_number,
            "session_string": session_str
        }
    except Exception as e:
        error_str = str(e)
        if "PASSWORD_HASH_INVALID" in error_str:
            return {"error": "invalid_password"}
        else:
            logger.error(f"Pyrogram 2FA check failed: {e}")
            try:
                await app.disconnect()
            except Exception:
                pass
            active_clients.pop(user_id, None)
            return {"error": error_str}


async def cancel_login(user_id):
    state = active_clients.pop(user_id, None)
    if state:
        try:
            await state["client"].disconnect()
        except Exception:
            pass


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
