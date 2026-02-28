# YouTube → Discord Upload Bot

Polls YouTube RSS feeds and posts new video notifications to Discord channels. Uses slash commands to manage subscriptions, backed by SQLite.

## Setup

### 1. Create a Discord Bot

1. Go to https://discord.com/developers/applications and create a new application
2. Under **Bot**, create a bot and copy the token
3. Under **OAuth2 → URL Generator**, select scopes: `bot`, `applications.commands`
4. Select bot permissions: `Send Messages`, `Embed Links`
5. Use the generated URL to invite the bot to your server

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and paste your bot token
```

### 4. Run

```bash
python bot.py
```

The bot will create `subscriptions.db` automatically on first run.

---

## Commands

| Command | Description | Permission Required |
|---|---|---|
| `/subscribe @handle #channel` | Subscribe to a YouTube channel, posting new videos to a Discord channel | Manage Channels |
| `/unsubscribe @handle` | Remove a subscription | Manage Channels |
| `/list` | Show all active subscriptions for this server | None |

### Example

```
/subscribe handle:@MrBeast channel:#youtube-feeds
```

---

## How It Works

- **Polling interval:** Every 10 minutes (configurable via `POLL_INTERVAL_SECONDS` in `poller.py`)
- **Channel ID discovery:** On `/subscribe`, the bot fetches the YouTube channel page and scrapes the `channelId` from the embedded page data — no API key required
- **Deduplication:** Video IDs are stored in the `seen_videos` table so the same video is never posted twice
- **Multiple subscriptions:** You can subscribe to as many channels as you want, each posting to its own Discord channel

## File Structure

```
bot.py          # Discord bot, slash commands
poller.py       # Background RSS polling loop
db.py           # SQLite helpers
requirements.txt
.env.example
```
