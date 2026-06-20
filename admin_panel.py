import streamlit as st
import pymongo
import pandas as pd
from datetime import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

MONGO_URI = config.MONGODB_URI
MONGO_DB = config.MONGODB_DB_NAME
SESSIONS_LOG = config.SESSIONS_LOG

st.set_page_config(
    page_title="🔞 Spicy Motivation Bot - Admin Panel",
    page_icon="🔞",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header { font-size: 2.5rem; color: #ff4757; text-align: center; }
    .sub-header { font-size: 1.2rem; color: #2ed573; text-align: center; }
    .stat-card { background: #1e1e2e; border-radius: 10px; padding: 20px; text-align: center; }
    .stat-number { font-size: 2rem; font-weight: bold; color: #ffa502; }
    .stat-label { font-size: 0.9rem; color: #dfe6e9; }
    .success-badge { color: #2ed573; font-weight: bold; }
    .danger-badge { color: #ff4757; font-weight: bold; }
    .warning-badge { color: #ffa502; font-weight: bold; }
    .info-badge { color: #1e90ff; font-weight: bold; }
    .purchase-card { background: #2d2d44; border-radius: 8px; padding: 15px; margin: 10px 0; border-left: 4px solid #ffa502; }
    .purchase-approved { border-left-color: #2ed573; }
    .purchase-rejected { border-left-color: #ff4757; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_mongo_client():
    return pymongo.MongoClient(MONGO_URI)


def get_db():
    client = get_mongo_client()
    return client[MONGO_DB]


def init_session_state():
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"
    if "broadcast_progress" not in st.session_state:
        st.session_state.broadcast_progress = None


def read_sessions_log():
    try:
        if not os.path.exists(SESSIONS_LOG):
            return "No session log file found."
        with open(SESSIONS_LOG, "r", encoding="utf-8") as f:
            content = f.read()
        return content if content else "Empty log."
    except Exception as e:
        return f"Error reading log: {e}"


def main():
    init_session_state()

    st.markdown("<h1 class='main-header'>🔞 SPICY MOTIVATION BOT</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Admin Control Panel — MongoDB Backed</p>", unsafe_allow_html=True)
    st.divider()

    with st.sidebar:
        st.markdown("### 🎛️ NAVIGATION")
        pages = {
            "📊 Dashboard": "dashboard",
            "📹 Video Management": "videos",
            "📦 Services": "services",
            "💰 Purchase Requests": "purchases",
            "📢 Broadcast": "broadcast",
            "🔒 Subscription": "subscription",
            "👥 Users": "users",
            "📋 Session Logs": "session_logs",
            "⚙️ Settings": "settings",
        }
        for label, page_id in pages.items():
            if st.button(label, use_container_width=True,
                         type="primary" if st.session_state.page == page_id else "secondary"):
                st.session_state.page = page_id
                st.rerun()

        st.divider()
        st.markdown(f"<small>🔞 Bot v2.0 — MongoDB</small>", unsafe_allow_html=True)
        st.markdown(f"<small>🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}</small>", unsafe_allow_html=True)

    if st.session_state.page == "dashboard":
        show_dashboard()
    elif st.session_state.page == "videos":
        show_video_management()
    elif st.session_state.page == "purchases":
        show_purchase_requests()
    elif st.session_state.page == "broadcast":
        show_broadcast()
    elif st.session_state.page == "subscription":
        show_subscription()
    elif st.session_state.page == "services":
        show_services()
    elif st.session_state.page == "users":
        show_users()
    elif st.session_state.page == "session_logs":
        show_session_logs()
    elif st.session_state.page == "settings":
        show_settings()


def show_dashboard():
    st.markdown("## 📊 DASHBOARD")
    db = get_db()

    user_count = db.users.count_documents({})
    video_count = db.videos.count_documents({})
    pending_purchases = db.purchases.count_documents({"status": "pending"})
    approved_purchases = db.purchases.count_documents({"status": "approved"})
    active_users = db.users.count_documents({"status": {"$in": ["active", "purchased"]}})
    purchased_users = db.users.count_documents({"status": "purchased"})

    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$times_watched"}}}]
    total_watches_result = list(db.videos.aggregate(pipeline))
    total_watches = total_watches_result[0]["total"] if total_watches_result else 0

    pipeline2 = [{"$group": {"_id": None, "total": {"$sum": "$total_watch_time"}}}]
    watch_time_result = list(db.users.aggregate(pipeline2))
    total_watch_time = watch_time_result[0]["total"] if watch_time_result else 0

    referral_count = db.referral_log.count_documents({})

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{user_count}</div>
            <div class="stat-label">👥 Total Users</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{video_count}</div>
            <div class="stat-label">📹 Total Videos</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{active_users}</div>
            <div class="stat-label">✅ Active Users</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{pending_purchases}</div>
            <div class="stat-label">⏳ Pending Purchases</div>
        </div>
        """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{approved_purchases}</div>
            <div class="stat-label">💰 Approved Purchases</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{purchased_users}</div>
            <div class="stat-label">💎 Premium Users</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{total_watches}</div>
            <div class="stat-label">🎬 Total Video Watches</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{referral_count}</div>
            <div class="stat-label">🎁 Total Referrals</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 📈 Quick Stats")
    st.markdown(f"""
    - ⏱️ Total Watch Time: **{total_watch_time // 60} minutes** ({total_watch_time} seconds)
    - 📊 Avg Watches/User: **{total_watches / max(user_count, 1):.1f}**
    - 💰 Conversion Rate: **{(purchased_users / max(active_users, 1) * 100):.1f}%**
    """)

    st.markdown("### 🏆 Top Users (Leaderboard)")
    top_users = list(db.users.find().sort("video_count", -1).limit(10))
    if top_users:
        data = []
        for i, u in enumerate(top_users, 1):
            data.append({
                "Rank": i,
                "User ID": u.get("user_id"),
                "Username": f"@{u.get('username', 'N/A')}",
                "Videos Watched": u.get("video_count", 0),
                "Watch Time (min)": u.get("total_watch_time", 0) // 60,
                "Pack": u.get("purchased_pack") or "Free",
            })
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    else:
        st.info("No users yet.")


def show_video_management():
    st.markdown("## 📹 VIDEO MANAGEMENT")
    db = get_db()

    col1, col2 = st.columns([2, 1])

    with col2:
        st.markdown("### 📥 Add New Video")
        upload_mode = st.radio("Upload Method", ["Telegram File ID", "Direct MP4 File Upload"])

        if upload_mode == "Telegram File ID":
            with st.form("add_video_form"):
                file_id = st.text_input("Video File ID", placeholder="Telegram file_id")
                caption = st.text_area("Caption", placeholder="Leave blank for auto-generated")
                category = st.selectbox(
                    "Category",
                    ["motivation", "fitness", "business", "mindset", "sports", "funny"],
                    index=0
                )
                delete_after = st.slider("Delete After (seconds)", 10, 300, 60)
                is_free = st.checkbox("Free Video (unlocked for all)", value=True)

                if st.form_submit_button("💾 SAVE VIDEO", type="primary", use_container_width=True):
                    if file_id:
                        counter = db.counters.find_one_and_update(
                            {"_id": "video_id"},
                            {"$inc": {"seq": 1}},
                            return_document=True,
                        )
                        vid = counter["seq"]
                        db.videos.insert_one({
                            "id": vid,
                            "file_id": file_id,
                            "caption": caption if caption else None,
                            "category": category,
                            "delete_after": delete_after,
                            "is_free": 1 if is_free else 0,
                            "added_by": 0,
                            "added_at": datetime.utcnow(),
                            "times_watched": 0,
                        })
                        st.success(f"✅ Video #{vid} added to {category}!")
                        st.rerun()
                    else:
                        st.error("❌ File ID is required.")
        else:
            uploaded_file = st.file_uploader("Upload Video File (.mp4)", type=["mp4"])
            caption = st.text_area("Caption", placeholder="Leave blank for auto-generated", key="direct_caption")
            category = st.selectbox(
                "Category",
                ["motivation", "fitness", "business", "mindset", "sports", "funny"],
                index=0,
                key="direct_category"
            )
            delete_after = st.slider("Delete After (seconds)", 10, 300, 60, key="direct_delete")
            is_free = st.checkbox("Free Video (unlocked for all)", value=True, key="direct_free")

            if st.button("🍆 UPLOAD & SAVE", type="primary", use_container_width=True):
                if uploaded_file is not None:
                    with st.spinner("Uploading to Telegram..."):
                        import requests
                        # Send to the first admin ID or log group ID
                        chat_id = config.LOG_GROUP_ID if config.LOG_GROUP_ID != 0 else config.ADMIN_IDS[0]
                        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendVideo"
                        files = {"video": (uploaded_file.name, uploaded_file.getvalue(), "video/mp4")}
                        data = {"chat_id": chat_id, "caption": "Uploaded via Streamlit Admin Panel"}
                        try:
                            response = requests.post(url, files=files, data=data, timeout=120)
                            if response.status_code == 200 and response.json().get("ok"):
                                res_json = response.json()
                                file_id = res_json["result"]["video"]["file_id"]

                                counter = db.counters.find_one_and_update(
                                    {"_id": "video_id"},
                                    {"$inc": {"seq": 1}},
                                    return_document=True,
                                )
                                vid = counter["seq"]
                                db.videos.insert_one({
                                    "id": vid,
                                    "file_id": file_id,
                                    "caption": caption if caption else None,
                                    "category": category,
                                    "delete_after": delete_after,
                                    "is_free": 1 if is_free else 0,
                                    "added_by": 0,
                                    "added_at": datetime.utcnow(),
                                    "times_watched": 0,
                                })
                                st.success(f"✅ Video #{vid} uploaded and saved to {category} successfully!")
                                st.rerun()
                            else:
                                err = response.json().get("description") if response.status_code == 200 else response.text
                                st.error(f"❌ Telegram upload failed: {err}")
                        except Exception as e:
                            st.error(f"❌ Error uploading video: {e}")
                else:
                    st.error("❌ Please select a video file first.")

    with col1:
        videos = list(db.videos.find().sort("added_at", -1))

        st.markdown(f"### All Videos ({len(videos)} total)")

        if not videos:
            st.warning("No videos yet. Add one!")
        else:
            video_data = []
            for v in videos:
                video_data.append({
                    "ID": v.get("id"),
                    "Category": v.get("category"),
                    "Free": "✅" if v.get("is_free") else "🔒",
                    "Delete": f"{v.get('delete_after', 60)}s",
                    "Watched": v.get("times_watched", 0),
                    "Added": str(v.get("added_at", ""))[:10] if v.get("added_at") else "N/A",
                })
            st.dataframe(pd.DataFrame(video_data), use_container_width=True, hide_index=True)

            st.markdown("### 🗑️ Delete Video")
            del_id = st.number_input("Video ID to delete", min_value=1, step=1)
            if st.button("🗑️ DELETE", type="secondary", use_container_width=True):
                db.videos.delete_one({"id": del_id})
                st.success(f"✅ Video #{del_id} deleted!")
                st.rerun()


def show_services():
    st.markdown("## 📦 SERVICE MANAGEMENT")
    db = get_db()
    
    with st.expander("➕ Add New Service", expanded=False):
        with st.form("add_service_form"):
            name = st.text_input("Service Name", placeholder="e.g. 50 Videos Pack")
            contact_text = st.text_area("Contact Owner Text", placeholder="Message shown when user clicks this service...", height=100)
            image_file_id = st.text_input("Image File ID (optional)", placeholder="Telegram file_id of an image to attach")
            if st.form_submit_button("💾 ADD SERVICE", type="primary", use_container_width=True):
                if name:
                    db.services.insert_one({
                        "name": name,
                        "contact_text": contact_text or "Contact owner for details.",
                        "image_file_id": image_file_id or None,
                        "created_at": datetime.utcnow(),
                    })
                    st.success(f"✅ Service '{name}' added!")
                    st.rerun()
                else:
                    st.error("❌ Service name is required.")
    
    services = list(db.services.find().sort("created_at", -1))
    if not services:
        st.warning("No services yet.")
    else:
        for s in services:
            with st.container():
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    st.markdown(f"**{s['name']}** (ID: {s['id']})")
                with c2:
                    if st.button("✏️ Edit", key=f"edit_svc_{s['id']}", use_container_width=True):
                        st.session_state.edit_service_id = s['id']
                        st.rerun()
                with c3:
                    if st.button("🗑️ Delete", key=f"del_svc_{s['id']}", use_container_width=True):
                        db.services.delete_one({"id": s['id']})
                        st.success(f"✅ Service '{s['name']}' deleted!")
                        st.rerun()
                with st.expander(f"📝 Details", expanded=False):
                    st.markdown(f"**Contact Text:** {s.get('contact_text', 'N/A')}")
                    st.markdown(f"**Image File ID:** `{s.get('image_file_id', 'None')}`")
        
        # Edit service modal
        if 'edit_service_id' in st.session_state:
            sid = st.session_state.edit_service_id
            svc = db.services.find_one({"id": sid})
            if svc:
                st.markdown("---")
                st.subheader(f"✏️ Edit: {svc['name']}")
                with st.form("edit_service_form"):
                    new_name = st.text_input("Name", value=svc.get('name', ''))
                    new_ct = st.text_area("Contact Text", value=svc.get('contact_text', ''), height=100)
                    new_img = st.text_input("Image File ID", value=svc.get('image_file_id', '') or '')
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.form_submit_button("💾 SAVE", type="primary", use_container_width=True):
                            db.services.update_one(
                                {"id": sid},
                                {"$set": {
                                    "name": new_name,
                                    "contact_text": new_ct,
                                    "image_file_id": new_img or None,
                                }}
                            )
                            st.success("✅ Service updated!")
                            del st.session_state.edit_service_id
                            st.rerun()
                    with col_b:
                        if st.form_submit_button("❌ CANCEL", use_container_width=True):
                            del st.session_state.edit_service_id
                            st.rerun()


def show_purchase_requests():
    st.markdown("## 💰 PURCHASE REQUESTS")
    db = get_db()

    tab1, tab2, tab3 = st.tabs(["⏳ Pending", "✅ Approved", "❌ Rejected"])

    with tab1:
        pending = list(db.purchases.find({"status": "pending"}).sort("requested_on", -1))

        if not pending:
            st.info("No pending purchase requests.")
        else:
            for p in pending:
                user = db.users.find_one({"user_id": p.get("user_id")})
                username = user.get("username", "N/A") if user else "N/A"

                with st.container():
                    st.markdown(f"""
                    <div class="purchase-card">
                        <h4>Request #{p.get('id')}</h4>
                        <p>👤 <b>User:</b> @{username} (ID: <code>{p.get('user_id')}</code>)</p>
                        <p>📦 <b>Pack:</b> {p.get('pack_name')} — <b>{p.get('amount')}</b></p>
                        <p>🕐 <b>Requested:</b> {p.get('requested_on')}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    col_a, col_b, col_c = st.columns([1, 1, 2])
                    with col_a:
                        if st.button(f"✅ Approve #{p.get('id')}", key=f"app_{p.get('id')}",
                                     type="primary", use_container_width=True):
                            db.purchases.update_one(
                                {"id": p.get("id")},
                                {"$set": {"status": "approved", "approved_on": datetime.utcnow()}}
                            )
                            db.users.update_one(
                                {"user_id": p.get("user_id")},
                                {"$set": {
                                    "status": "purchased",
                                    "purchased_pack": p.get("pack_name"),
                                    "purchase_date": datetime.utcnow(),
                                }}
                            )
                            st.success(f"✅ Purchase #{p.get('id')} approved!")
                            st.rerun()
                    with col_b:
                        if st.button(f"❌ Reject #{p.get('id')}", key=f"rej_{p.get('id')}",
                                     type="secondary", use_container_width=True):
                            db.purchases.update_one(
                                {"id": p.get("id")},
                                {"$set": {"status": "rejected"}}
                            )
                            st.warning(f"❌ Purchase #{p.get('id')} rejected!")
                            st.rerun()

    with tab2:
        approved = list(db.purchases.find({"status": "approved"}).sort("approved_on", -1).limit(20))
        if approved:
            data = []
            for a in approved:
                user = db.users.find_one({"user_id": a.get("user_id")})
                data.append({
                    "ID": a.get("id"),
                    "User": f"@{user.get('username', a.get('user_id'))}" if user else a.get("user_id"),
                    "Pack": a.get("pack_name"),
                    "Amount": a.get("amount"),
                    "Approved": str(a.get("approved_on", ""))[:19] if a.get("approved_on") else "N/A",
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
        else:
            st.info("No approved purchases.")

    with tab3:
        rejected = list(db.purchases.find({"status": "rejected"}).sort("requested_on", -1).limit(20))
        if rejected:
            data = []
            for r in rejected:
                user = db.users.find_one({"user_id": r.get("user_id")})
                data.append({
                    "ID": r.get("id"),
                    "User": f"@{user.get('username', r.get('user_id'))}" if user else r.get("user_id"),
                    "Pack": r.get("pack_name"),
                    "Amount": r.get("amount"),
                    "Requested": str(r.get("requested_on", ""))[:19],
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
        else:
            st.info("No rejected purchases.")


def show_broadcast():
    st.markdown("## 📢 BROADCAST CENTER")
    st.markdown("Send messages to targeted user groups.")

    db = get_db()

    tabs = st.tabs(["✏️ Custom Message", "📋 Templates"])

    with tabs[0]:
        with st.form("broadcast_form"):
            target = st.selectbox(
                "🎯 Target Audience",
                [
                    ("all", "👥 All Users"),
                    ("active", "✅ Active Users"),
                    ("pending", "⏳ Pending Users"),
                    ("purchased", "💰 Purchased Users"),
                ],
                format_func=lambda x: x[1],
            )
            msg_text = st.text_area(
                "Message (HTML supported)",
                placeholder="<b>Your message here</b>\n\nUse <i>HTML</i> formatting...",
                height=200,
            )

            if st.form_submit_button("📤 SEND BROADCAST", type="primary", use_container_width=True):
                if msg_text:
                    target_key = target[0]
                    query = {}
                    if target_key == "active":
                        query = {"status": {"$in": ["active", "purchased"]}}
                    elif target_key == "pending":
                        query = {"status": "pending"}
                    elif target_key == "purchased":
                        query = {"status": "purchased"}

                    users = list(db.users.find(query))
                    total = len(users)
                    success = 0
                    failed = 0

                    progress_bar = st.progress(0, text="Sending...")

                    for i, u in enumerate(users):
                        try:
                            from telegram import Bot
                            import asyncio
                            bot = Bot(token=config.BOT_TOKEN)
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(
                                bot.send_message(chat_id=u["user_id"], text=msg_text, parse_mode="HTML")
                            )
                            loop.close()
                            success += 1
                        except Exception as e:
                            failed += 1

                        if (i + 1) % 5 == 0 or i == total - 1:
                            progress_bar.progress(
                                (i + 1) / total,
                                text=f"Sent: {i + 1}/{total} | ✅ {success} | ❌ {failed}"
                            )

                    db.broadcasts.insert_one({
                        "message": msg_text[:500],
                        "media_type": "text",
                        "target": target_key,
                        "sent_at": datetime.utcnow(),
                        "status": "sent",
                        "delivered_count": success,
                        "failed_count": failed,
                    })
                    st.success(
                        f"✅ Broadcast complete!\n\n"
                        f"📊 Results:\n"
                        f"• Target: {total} users\n"
                        f"• ✅ Sent: {success}\n"
                        f"• ❌ Failed: {failed}"
                    )
                else:
                    st.error("❌ Message cannot be empty.")

    with tabs[1]:
        try:
            with open("templates/broadcast_templates.json", "r", encoding="utf-8") as f:
                templates = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            templates = {}

        if not templates:
            st.warning("No templates found.")
        else:
            for name, tmpl in templates.items():
                with st.expander(f"📋 {tmpl.get('name', name)}"):
                    st.code(tmpl.get("text", ""), language="html")
                    st.caption(f"Target: {tmpl.get('target', 'all')}")


def show_subscription():
    st.markdown("## 🔒 FORCE SUBSCRIPTION")
    db = get_db()

    sub = db.subscriptions.find_one({"_id": "config"})

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Current Settings")
        if sub:
            st.markdown(f"""
            - **Channel Username:** `{sub.get('channel_username', 'N/A')}`
            - **Channel ID/Link:** `{sub.get('channel_id', 'N/A')}`
            - **Active:** {'✅ Yes' if sub.get('is_active') else '❌ No'}
            """)
        else:
            st.warning("No subscription channel configured.")

    with col2:
        st.markdown("### Update Channel")
        with st.form("sub_form"):
            new_username = st.text_input("Channel Username", value=sub.get("channel_username", "@channel") if sub else "@channel")
            new_link = st.text_input("Invite Link", value=sub.get("channel_id", "https://t.me/") if sub else "https://t.me/")
            is_active = st.checkbox("Active", value=sub.get("is_active", True) if sub else True)

            if st.form_submit_button("💾 SAVE", type="primary", use_container_width=True):
                db.subscriptions.update_one(
                    {"_id": "config"},
                    {"$set": {
                        "channel_username": new_username,
                        "channel_id": new_link,
                        "is_active": is_active,
                    }},
                    upsert=True,
                )
                st.success("✅ Subscription settings saved!")
                st.rerun()


def show_users():
    st.markdown("## 👥 USER MANAGEMENT")
    db = get_db()

    users = list(db.users.find().sort("last_active", -1))

    if not users:
        st.info("No users registered yet.")
    else:
        data = []
        for u in users:
            data.append({
                "ID": u.get("user_id"),
                "Username": f"@{u.get('username', 'N/A')}",
                "Status": u.get("status", "pending"),
                "Videos": u.get("video_count", 0),
                "Watch Time": f"{u.get('total_watch_time', 0) // 60}m",
                "Pack": u.get("purchased_pack") or "Free",
                "Referrals": u.get("referral_count", 0),
                "Last Active": str(u.get("last_active", ""))[:16] if u.get("last_active") else "N/A",
            })

        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            total = len(users)
            active = sum(1 for u in users if u.get("status") in ("active", "purchased"))
            purchased = sum(1 for u in users if u.get("status") == "purchased")
            st.metric("Total Users", total)
            st.metric("Active Users", active)
            st.metric("Premium Users", purchased)


def show_session_logs():
    st.markdown("## 📋 SESSION LOGS")
    content = read_sessions_log()

    lines = content.split("\n")
    st.caption(f"Total lines: {len(lines)}")

    max_lines = st.slider("Lines to show", 10, min(200, len(lines)), 50)
    recent = "\n".join(lines[-max_lines:])

    st.text_area("Log Content", recent, height=500)

    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()


def show_settings():
    st.markdown("## ⚙️ GLOBAL SETTINGS")
    db = get_db()
    
    settings = db.settings.find_one({"_id": "global_config"}) or {}
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ⚙️ Update Configs")
        with st.form("settings_form"):
            force_sub = st.text_input("Force Join Channel", value=settings.get("force_sub_channel", ""))
            force_link = st.text_input("Force Join Invite Link", value=settings.get("channel_invite_link", ""))
            log_group = st.number_input("Log Group ID", value=int(settings.get("log_group_id", 0)), step=1)
            brand_name = st.text_input("Branding Name", value=settings.get("branding_name", "Spicy Motivation Bot"))
            brand_days = st.number_input("Branding Days", value=int(settings.get("branding_days", 30)), min_value=1)
            owner_username = st.text_input("Owner Username", value=settings.get("owner_username", config.OWNER_USERNAME))
            upi = st.text_input("UPI ID", value=settings.get("upi_id", ""))
            usdt = st.text_input("USDT Address", value=settings.get("usdt_address", ""))
            ton = st.text_input("TON Address", value=settings.get("ton_address", ""))
            auto_join = st.text_input("Auto-Join Channel/Link", value=settings.get("auto_join_channel", ""))
            commission = st.number_input("Commission %", value=int(settings.get("commission", 10)), min_value=0, max_value=100)
            maint_mode = st.checkbox("Maintenance Mode Enabled", value=bool(settings.get("maintenance_mode", False)))
            
            if st.form_submit_button("💾 SAVE SETTINGS", type="primary", use_container_width=True):
                db.settings.update_one(
                    {"_id": "global_config"},
                    {"$set": {
                        "force_sub_channel": force_sub,
                        "channel_invite_link": force_link,
                        "log_group_id": int(log_group),
                        "branding_name": brand_name,
                        "branding_days": int(brand_days),
                        "owner_username": owner_username,
                        "upi_id": upi,
                        "usdt_address": usdt,
                        "ton_address": ton,
                        "auto_join_channel": auto_join,
                        "commission": int(commission),
                        "maintenance_mode": maint_mode,
                    }},
                    upsert=True
                )
                st.success("✅ Settings updated successfully!")
                st.rerun()
                
    with col2:
        st.markdown("### 📋 Current Bot Settings")
        st.markdown(f"""
        - **Token:** `{config.BOT_TOKEN[:10]}...{config.BOT_TOKEN[-5:]}` (hidden)
        - **Admin IDs:** `{config.ADMIN_IDS}`
        - **Free Previews:** `{config.FREE_PREVIEW_COUNT}`
        - **Video Delete Timer:** `{config.VIDEO_DELETE_AFTER}s`
        - **OTP Login:** `{'Enabled' if config.OTP_LOGIN_ENABLED else 'Disabled'}`
        - **Owner:** `{config.OWNER_USERNAME}`
        - **Bot Link:** `{config.BOT_LINK}`
        """)
        
        st.markdown("### 🗄️ MongoDB Database Info")
        st.markdown(f"""
        - **URI:** `{config.MONGODB_URI}`
        - **Database:** `{config.MONGODB_DB_NAME}`
        """)

    st.divider()
    st.markdown("### 📦 Export Data")
    if st.button("📥 Export Users CSV", use_container_width=True):
        users = list(db.users.find())
        if users:
            data = []
            for u in users:
                data.append({
                    "user_id": u.get("user_id"),
                    "username": u.get("username"),
                    "status": u.get("status"),
                    "video_count": u.get("video_count", 0),
                    "total_watch_time": u.get("total_watch_time", 0),
                    "purchased_pack": u.get("purchased_pack"),
                    "referral_count": u.get("referral_count", 0),
                })
            df = pd.DataFrame(data)
            csv = df.to_csv(index=False)
            st.download_button(
                "⬇️ Download CSV",
                csv,
                f"users_export_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True,
            )
        else:
            st.warning("No users to export.")

    st.divider()
    st.markdown("### 🚨 Danger Zone")
    with st.expander("⚠️ Clear All Purchase Requests"):
        if st.button("🗑️ Clear All Requests", type="secondary", use_container_width=True):
            db.purchases.delete_many({})
            st.success("All purchase requests cleared!")
            st.rerun()


if __name__ == "__main__":
    main()
