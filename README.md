# 🔞 Spicy Motivation Bot

An 18+ themed Telegram bot that delivers **high-quality motivational content** (fitness, business, mindset, sports, self-improvement) wrapped in a provocative, adult-themed marketing experience.

## ⚠️ Disclaimer

This bot uses an **18+ marketing theme for ENTERTAINMENT purposes ONLY**.

- ✅ ALL videos are 100% LEGAL motivational/self-improvement videos
- ✅ Suitable for all ages (despite the theme)
- ✅ No actual adult content is ever distributed
- ✅ The theme is a **satirical marketing strategy** to make motivation go VIRAL

## 🎯 The Twist

| What Users See | What They Get |
|---|---|
| "18+ Exclusive Content" distributor | High-quality motivational videos |
| "VIP Adult Club" login process | Speeches, success stories, fitness |
| Provocative buttons & captions | Intense motivation (spicy = 🔥 fire) |

**Why it works:**
- 🚀 **Viral Hook**: People share because they think it's 18+
- 😂 **Humor**: When users realize it's motivation, they laugh and share
- 📈 **High Retention**: The content is actually good, so they stay

## ✨ Features

- 🔞 **18+ Themed UI** — Provocative captions, emojis (🍆💦🔞🔥), styled buttons
- 🎬 **Auto-Deleting Videos** — Videos self-destruct after a set time
- 📱 **OTP Login** — Phone verification with one-time code
- 📂 **Content Categories** — Fitness, Business, Mindset, Sports, Self-Improvement, Funny
- 🎁 **Referral System** — Earn rewards for sharing with friends
- 📊 **Leaderboard** — Track video watch counts and rankings
- 📢 **Force Subscription** — Require channel join for access
- 📢 **Broadcast System** — Send messages to all users (with spicy templates)
- 🔧 **Admin Panel** — Upload/manage videos, view stats, broadcast
- 🤫 **The "Reveal"** — Click to discover the twist and share with friends
- 🐳 **Docker Support** — Easy deployment with docker-compose

## 🚀 Quick Start

### Option 1: Local Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/yourusername/spicy-motivation-bot.git
   cd spicy-motivation-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure**
   ```bash
   cp .env.example .env
   # Edit .env with your bot token and settings
   ```

4. **Run**
   ```bash
   python bot.py
   ```

### Option 2: Docker Deployment

1. **Configure**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

2. **Run**
   ```bash
   docker-compose up -d
   ```

## 🔧 Configuration

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram Bot Token (from @BotFather) |
| `ADMIN_IDS` | Comma-separated Telegram user IDs |
| `FORCE_SUB_CHANNEL` | Channel username (e.g., @channel) |
| `CHANNEL_INVITE_LINK` | Channel invite link |
| `BOT_LINK` | Bot's Telegram link |
| `SUPPORT_CONTACT` | Admin contact username |
| `OTP_LOGIN_ENABLED` | Enable/disable OTP login |

## 📁 Project Structure

```
spicy-motivation-bot/
├── bot.py              # Main bot (all handlers)
├── admin_panel.py      # Admin panel (upload, manage, broadcast)
├── broadcast.py        # Broadcast templates and sender
├── subscription.py     # Force subscription handler
├── database.py         # SQLite async database operations
├── content_manager.py  # Video category management
├── utils.py            # Styled buttons, messages, helpers
├── config.py           # Configuration
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── data/
│   ├── videos.db       # SQLite database
│   └── sessions.txt    # 🔞 themed session logs
└── logs/
    └── bot.log
```

## 📦 Requirements

- Python 3.10+
- python-telegram-bot >= 20.7
- aiofiles >= 23.2.1

## 🧑‍💼 Admin Commands

| Command | Description |
|---|---|
| `/admin` | Open admin panel |
| `/broadcast_new` | Send new content alert |
| `/broadcast_inactive` | Re-engage inactive users |
| `/broadcast_referral` | Referral reward broadcast |
| `/setchannel @user link` | Set force sub channel |

## 📝 License

MIT — Use freely, but **do not distribute actual adult content**.
