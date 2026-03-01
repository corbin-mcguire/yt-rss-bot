# Changelog

All notable changes to this project will be documented here.

## [Unreleased]

## [0.1.0] - 2026-03-01

### Added
- `/subscribe` command — subscribe to a YouTube channel by handle or channel ID, posting new uploads to a Discord channel
- `/unsubscribe` command — remove a subscription
- `/list` command — show all active subscriptions for the server
- `/directions` command — help text for finding a YouTube channel ID manually
- Background RSS polling loop (every 10 minutes)
- Channel ID discovery via YouTube page scraping (no API key required)
- SQLite-backed deduplication to avoid reposting videos
- Docker support with named volume for persistent storage
- Helper scripts: `build.sh`, `run.sh`, `stop.sh`, `restart.sh`, `logs.sh`, `shell.sh`
