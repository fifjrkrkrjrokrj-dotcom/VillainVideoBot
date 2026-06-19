from datetime import datetime
import motor.motor_asyncio
import config

client = None
db = None


async def init_db():
    global client, db
    client = motor.motor_asyncio.AsyncIOMotorClient(config.MONGODB_URI)
    db = client[config.MONGODB_DB_NAME]

    await db.counters.update_one(
        {"_id": "video_id"},
        {"$setOnInsert": {"seq": 0}},
        upsert=True
    )
    await db.counters.update_one(
        {"_id": "purchase_id"},
        {"$setOnInsert": {"seq": 0}},
        upsert=True
    )
    await db.counters.update_one(
        {"_id": "broadcast_id"},
        {"$setOnInsert": {"seq": 0}},
        upsert=True
    )

    existing = await db.subscriptions.find_one({"_id": "config"})
    if not existing:
        await db.subscriptions.insert_one({
            "_id": "config",
            "channel_username": config.FORCE_SUB_CHANNEL,
            "channel_id": config.CHANNEL_INVITE_LINK,
            "is_active": True,
            "added_on": datetime.utcnow(),
        })

    existing_settings = await db.settings.find_one({"_id": "global_config"})
    if not existing_settings:
        await db.settings.insert_one({
            "_id": "global_config",
            "force_sub_channel": config.FORCE_SUB_CHANNEL,
            "channel_invite_link": config.CHANNEL_INVITE_LINK,
            "log_group_id": config.LOG_GROUP_ID,
            "branding_name": "Spicy Motivation Bot",
            "branding_days": 30,
            "upi_id": "",
            "usdt_address": "",
            "ton_address": "",
            "maintenance_mode": False,
            "admin_ids": config.ADMIN_IDS,
            "auto_join_channel": "",
        })

    await db.users.create_index("user_id", unique=True)
    await db.videos.create_index("id", unique=True)
    await db.purchases.create_index("id", unique=True)
    await db.activity_log.create_index([("timestamp", -1)])

    print(f"✅ MongoDB connected: {config.MONGODB_URI}/{config.MONGODB_DB_NAME}")


async def _next_id(counter_name):
    result = await db.counters.find_one_and_update(
        {"_id": counter_name},
        {"$inc": {"seq": 1}},
        return_document=True,
    )
    return result["seq"]


async def add_user(user_id, username, first_name):
    existing = await db.users.find_one({"user_id": user_id})
    if not existing:
        await db.users.insert_one({
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "phone": None,
            "status": "pending",
            "login_time": None,
            "video_count": 0,
            "total_watch_time": 0,
            "referred_by": None,
            "referral_count": 0,
            "purchased_pack": None,
            "purchase_date": None,
            "pack_expiry": None,
            "free_previews_used": 0,
            "last_video_id": None,
            "language": None,
            "agreement_accepted": False,
            "session_string": None,
            "last_active": datetime.utcnow(),
            "joined_at": datetime.utcnow(),
        })


async def get_user(user_id):
    return await db.users.find_one({"user_id": user_id})


async def update_user(user_id, **kwargs):
    kwargs["last_active"] = datetime.utcnow()
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": kwargs}
    )


async def log_activity(user_id, action, details=""):
    await db.activity_log.insert_one({
        "user_id": user_id,
        "action": action,
        "details": details,
        "timestamp": datetime.utcnow(),
    })


async def add_video(file_id, caption, category, delete_after, added_by, is_free=1):
    vid = await _next_id("video_id")
    await db.videos.insert_one({
        "id": vid,
        "file_id": file_id,
        "caption": caption,
        "category": category,
        "delete_after": delete_after,
        "is_free": is_free,
        "added_by": added_by,
        "added_at": datetime.utcnow(),
        "times_watched": 0,
    })
    return vid


async def get_video(video_id):
    return await db.videos.find_one({"id": video_id})


async def get_videos_by_category(category, limit=10, only_free=False):
    query = {"category": category}
    if only_free:
        query["is_free"] = 1
    cursor = db.videos.find(query).sort("added_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_random_video(exclude_ids=None, only_free=False):
    query = {}
    if only_free:
        query["is_free"] = 1
    if exclude_ids:
        query["id"] = {"$nin": exclude_ids}

    cursor = db.videos.aggregate([
        {"$match": query},
        {"$sample": {"size": 1}},
    ])
    result = await cursor.to_list(length=1)
    return result[0] if result else None


async def increment_watch_count(video_id):
    await db.videos.update_one(
        {"id": video_id},
        {"$inc": {"times_watched": 1}}
    )


async def get_all_videos():
    cursor = db.videos.find().sort("added_at", -1)
    return await cursor.to_list(length=None)


async def delete_video(video_id):
    await db.videos.delete_one({"id": video_id})


async def video_count():
    return await db.videos.count_documents({})


async def get_user_count():
    return await db.users.count_documents({})


async def get_users_by_status(status):
    cursor = db.users.find({"status": status}).sort("last_active", -1)
    return await cursor.to_list(length=None)


async def get_all_users():
    cursor = db.users.find().sort("last_active", -1)
    return await cursor.to_list(length=None)


async def get_active_users():
    cursor = db.users.find({"status": {"$in": ["active", "purchased"]}}).sort("last_active", -1)
    return await cursor.to_list(length=None)


async def get_purchased_users():
    cursor = db.users.find({"status": "purchased"}).sort("last_active", -1)
    return await cursor.to_list(length=None)


async def increment_referral(user_id):
    await db.users.update_one(
        {"user_id": user_id},
        {"$inc": {"referral_count": 1}}
    )


async def log_referral(referrer_id, referred_id):
    await db.referral_log.insert_one({
        "referrer_id": referrer_id,
        "referred_id": referred_id,
        "joined_at": datetime.utcnow(),
    })


async def get_leaderboard(limit=10):
    cursor = db.users.find().sort("video_count", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def create_purchase(user_id, pack_name, amount):
    pid = await _next_id("purchase_id")
    await db.purchases.insert_one({
        "id": pid,
        "user_id": user_id,
        "pack_name": pack_name,
        "amount": amount,
        "status": "pending",
        "requested_on": datetime.utcnow(),
        "approved_on": None,
    })
    return pid


async def get_pending_purchases():
    cursor = db.purchases.find({"status": "pending"}).sort("requested_on", -1)
    return await cursor.to_list(length=None)


async def get_all_purchases():
    cursor = db.purchases.find().sort("requested_on", -1)
    return await cursor.to_list(length=None)


async def approve_purchase(purchase_id):
    purchase = await db.purchases.find_one({"id": purchase_id})
    if not purchase:
        return None

    await db.purchases.update_one(
        {"id": purchase_id},
        {"$set": {"status": "approved", "approved_on": datetime.utcnow()}}
    )
    await db.users.update_one(
        {"user_id": purchase["user_id"]},
        {"$set": {
            "status": "purchased",
            "purchased_pack": purchase["pack_name"],
            "purchase_date": datetime.utcnow(),
        }}
    )
    return purchase


async def reject_purchase(purchase_id):
    await db.purchases.update_one(
        {"id": purchase_id},
        {"$set": {"status": "rejected"}}
    )


async def create_broadcast(message, media_type="text", media_id=None, target="all"):
    bid = await _next_id("broadcast_id")
    await db.broadcasts.insert_one({
        "id": bid,
        "message": message,
        "media_type": media_type,
        "media_id": media_id,
        "target": target,
        "sent_at": datetime.utcnow(),
        "status": "sent",
        "delivered_count": 0,
        "failed_count": 0,
    })
    return bid


async def get_subscription():
    return await db.subscriptions.find_one({"_id": "config"})


async def update_subscription(channel_username, channel_id):
    await db.subscriptions.update_one(
        {"_id": "config"},
        {"$set": {
            "channel_username": channel_username,
            "channel_id": channel_id,
        }}
    )


async def get_activity_log(limit=50):
    cursor = db.activity_log.find().sort("timestamp", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_referral_count():
    return await db.referral_log.count_documents({})


async def save_broadcast_template(name, text, target="all"):
    await db.broadcast_templates.update_one(
        {"name": name},
        {"$set": {"name": name, "template_text": text, "target": target}},
        upsert=True,
    )


async def get_broadcast_templates():
    cursor = db.broadcast_templates.find()
    return await cursor.to_list(length=None)


async def get_settings():
    s = await db.settings.find_one({"_id": "global_config"})
    if not s:
        s = {
            "_id": "global_config",
            "force_sub_channel": config.FORCE_SUB_CHANNEL,
            "channel_invite_link": config.CHANNEL_INVITE_LINK,
            "log_group_id": config.LOG_GROUP_ID,
            "branding_name": "Spicy Motivation Bot",
            "branding_days": 30,
            "upi_id": "",
            "usdt_address": "",
            "ton_address": "",
            "maintenance_mode": False,
            "admin_ids": config.ADMIN_IDS,
            "auto_join_channel": "",
        }
        await db.settings.insert_one(s)
    return s


async def update_settings(**kwargs):
    await db.settings.update_one(
        {"_id": "global_config"},
        {"$set": kwargs},
        upsert=True
    )
