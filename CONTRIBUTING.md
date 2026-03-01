# Contributing

Thanks for your interest in contributing!

## Dev setup

1. Clone the repo
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install ruff
   ```
3. Copy `.env.example` to `.env` and add your Discord bot token

## Running locally

```bash
python bot.py
```

The bot will create `subscriptions.db` on first run.

## Code style

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
ruff check .
ruff format .
```

The CI workflow runs `ruff check` on every push and pull request.

## Submitting changes

1. Fork the repository
2. Create a branch: `git checkout -b my-feature`
3. Make your changes and verify the bot works end-to-end
4. Open a pull request against `main`

## Project structure

| File | Purpose |
|---|---|
| `bot.py` | Discord client and slash commands |
| `poller.py` | Background RSS polling loop |
| `db.py` | SQLite helpers |
