import asyncio
import logging
import os
import re

import aiohttp
import discord
from discord import app_commands
from dotenv import load_dotenv

import db
import poller

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TOKEN = os.environ["DISCORD_TOKEN"]


class YTBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        self.loop.create_task(poller.poll_loop(self))

    async def on_ready(self):
        logger.info("Logged in as %s (id: %s)", self.user, self.user.id)


bot = YTBot()


# ---------------------------------------------------------------------------
# /subscribe
# ---------------------------------------------------------------------------
_CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")


@bot.tree.command(name="subscribe", description="Subscribe to a YouTube channel's uploads.")
@app_commands.describe(
    handle="YouTube @handle (e.g. @MrBeast) or raw channel ID (e.g. UCxxxxxx...)",
    channel="Discord channel to post new videos in",
    nickname="Display name shown in /list and notifications (required when using a raw channel ID)",
)
@app_commands.checks.has_permissions(manage_channels=True)
async def subscribe(
    interaction: discord.Interaction,
    handle: str,
    channel: discord.TextChannel,
    nickname: str | None = None,
):
    await interaction.response.defer(ephemeral=True, thinking=True)

    handle = handle.strip().lstrip("@")

    if _CHANNEL_ID_RE.match(handle):
        # User supplied a raw channel ID — use it directly
        yt_channel_id = handle
        if not nickname:
            await interaction.followup.send(
                "❌ Please provide a `nickname` when subscribing by channel ID so it shows up "
                "clearly in `/list` and notifications (e.g. `nickname:MrBeast`).",
                ephemeral=True,
            )
            return
        yt_handle = nickname.strip()
    else:
        async with aiohttp.ClientSession() as session:
            yt_channel_id = await poller.fetch_channel_id(handle, session)

        if not yt_channel_id:
            await interaction.followup.send(
                f"❌ Couldn't find a YouTube channel for `@{handle}`. "
                "Double-check the handle, or look up the channel ID manually and pass it directly.",
                ephemeral=True,
            )
            return

        yt_handle = nickname.strip() if nickname else handle

    added = db.add_subscription(
        guild_id=str(interaction.guild_id),
        discord_channel_id=str(channel.id),
        yt_handle=yt_handle,
        yt_channel_id=yt_channel_id,
    )

    if added:
        await interaction.followup.send(
            f"✅ Subscribed to **@{yt_handle}**! New uploads will be posted in {channel.mention}.",
            ephemeral=True,
        )
        logger.info("Guild %s subscribed to @%s (%s)", interaction.guild_id, yt_handle, yt_channel_id)
    else:
        await interaction.followup.send(
            f"⚠️ This server is already subscribed to **@{yt_handle}**.",
            ephemeral=True,
        )


# ---------------------------------------------------------------------------
# /unsubscribe
# ---------------------------------------------------------------------------
@bot.tree.command(name="unsubscribe", description="Stop posting uploads from a YouTube channel.")
@app_commands.describe(handle="YouTube @handle to remove (e.g. @MrBeast)")
@app_commands.checks.has_permissions(manage_channels=True)
async def unsubscribe(interaction: discord.Interaction, handle: str):
    handle = handle.lstrip("@")
    removed = db.remove_subscription(str(interaction.guild_id), handle)

    if removed:
        await interaction.response.send_message(
            f"✅ Unsubscribed from **@{handle}**.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ No subscription found for **@{handle}** in this server.", ephemeral=True
        )


# ---------------------------------------------------------------------------
# /directions
# ---------------------------------------------------------------------------
@bot.tree.command(name="directions", description="How to find a YouTube channel ID for use with /subscribe.")
async def directions(interaction: discord.Interaction):
    embed = discord.Embed(
        title="How to Find a YouTube Channel ID",
        description=(
            "If `/subscribe` can't resolve a channel by handle, you can look up "
            "the channel ID manually and pass it directly.\n\n"
            "Channel IDs look like `UCxxxxxxxxxxxxxxxxxxxxxx` (24 characters)."
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="Method 1 — Channel URL",
        value=(
            "Visit the channel on YouTube. If the URL contains `/channel/`, "
            "the ID is right there:\n"
            "`https://www.youtube.com/channel/`**`UCxxxxxxxxxxxxxxxxxxxxxx`**"
        ),
        inline=False,
    )
    embed.add_field(
        name="Method 2 — Page source",
        value=(
            "1. Open the channel page in your browser\n"
            "2. Press **Ctrl+U** (or **Cmd+U**) to view source\n"
            '3. Search for `"channelId"` — the value next to it is the ID'
        ),
        inline=False,
    )
    embed.add_field(
        name="Using the ID",
        value='Pass it directly to `/subscribe`:\n`/subscribe handle:UCxxxxxxxxxxxxxxxxxxxxxx channel:#my-channel`',
        inline=False,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ---------------------------------------------------------------------------
# /list
# ---------------------------------------------------------------------------
@bot.tree.command(name="list", description="Show all active YouTube subscriptions for this server.")
async def list_subs(interaction: discord.Interaction):
    subs = db.get_subscriptions(str(interaction.guild_id))

    if not subs:
        await interaction.response.send_message(
            "No subscriptions yet. Use `/subscribe` to add one!", ephemeral=True
        )
        return

    lines = []
    for sub in subs:
        ch = f"<#{sub['discord_channel_id']}>"
        lines.append(f"• **@{sub['yt_handle']}** → {ch}")

    embed = discord.Embed(
        title="YouTube Subscriptions",
        description="\n".join(lines),
        color=discord.Color.red(),
    )
    embed.set_footer(text=f"{len(subs)} subscription(s)")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------
@subscribe.error
@unsubscribe.error
async def permission_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You need the **Manage Channels** permission to use this command.", ephemeral=True
        )
    else:
        logger.error("Command error: %s", error)
        await interaction.response.send_message(
            "❌ An unexpected error occurred.", ephemeral=True
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    db.init_db()
    bot.run(TOKEN)
