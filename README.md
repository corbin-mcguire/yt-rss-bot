# YouTube → Discord Upload Bot

Polls YouTube RSS feeds and posts new video notifications to Discord channels. Uses slash commands to manage subscriptions, backed by SQLite.

---

## Quick Start (Docker)

### 1. Create a Discord Bot

1. Go to https://discord.com/developers/applications and create a new application
2. Under **Bot**, create a bot and copy the token
3. Under **OAuth2 → URL Generator**, select scopes: `bot`, `applications.commands`
4. Select bot permissions: `Send Messages`, `Embed Links`
5. Use the generated URL to invite the bot to your server

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and paste your bot token
```

### 3. Build and run

```bash
./scripts/build.sh
./scripts/run.sh
```

The bot starts in the background. The SQLite database is stored in a named Docker volume (`bot-data`) and persists across restarts.

---

## Helper Scripts

| Script | Description |
|---|---|
| `./scripts/build.sh` | Build the Docker image |
| `./scripts/run.sh` | Start the bot in the background |
| `./scripts/stop.sh` | Stop the bot |
| `./scripts/restart.sh` | Restart the bot |
| `./scripts/logs.sh` | Follow live logs |
| `./scripts/shell.sh` | Open a shell inside the running container |

All scripts accept extra arguments that are forwarded to `docker compose`.

---

## Manual Setup (without Docker)

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run

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

---

## File Structure

```
bot.py              # Discord bot, slash commands
poller.py           # Background RSS polling loop
db.py               # SQLite helpers
requirements.txt
.env.example
docker/
  Dockerfile
  docker-compose.yml
scripts/
  build.sh
  run.sh
  stop.sh
  restart.sh
  logs.sh
  shell.sh
```

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `DISCORD_TOKEN` | *(required)* | Discord bot token |
| `DB_PATH` | `subscriptions.db` | Path to the SQLite database file |
