import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

import aiohttp
import discord

import db

logger = logging.getLogger(__name__)

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
POLL_INTERVAL_SECONDS = 10 * 60  # 10 minutes
BACKFILL_WINDOW = timedelta(days=7)


async def fetch_channel_id(handle: str, session: aiohttp.ClientSession) -> str | None:
    """Scrape the YouTube channel page to find the channel ID for a given @handle."""
    handle = handle.lstrip("@")
    url = f"https://www.youtube.com/@{handle}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; YTBot/1.0)"}

    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                logger.warning("Got status %s fetching %s", resp.status, url)
                return None
            html = await resp.text()
    except Exception as e:
        logger.error("Error fetching channel page for @%s: %s", handle, e)
        return None

    # YouTube embeds channel data in a JSON blob in the page source
    match = re.search(r'"channelId"\s*:\s*"(UC[\w-]{22})"', html)
    if match:
        return match.group(1)

    logger.warning("Could not find channelId in page for @%s", handle)
    return None


async def fetch_rss(channel_id: str, session: aiohttp.ClientSession) -> list[dict]:
    """Fetch the RSS feed for a channel and return a list of video dicts."""
    url = RSS_URL.format(channel_id=channel_id)
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                logger.warning("RSS fetch failed for %s (status %s)", channel_id, resp.status)
                return []
            text = await resp.text()
    except Exception as e:
        logger.error("Error fetching RSS for %s: %s", channel_id, e)
        return []

    # Parse the Atom feed with basic regex — keeps dependencies minimal
    videos = []
    entries = re.findall(r"<entry>(.*?)</entry>", text, re.DOTALL)
    for entry in entries:
        video_id = _extract(r"<yt:videoId>(.*?)</yt:videoId>", entry)
        title = _extract(r"<title>(.*?)</title>", entry)
        link = _extract(r'<link rel="alternate" href="(.*?)"', entry)
        author = _extract(r"<name>(.*?)</name>", entry)
        published = _extract(r"<published>(.*?)</published>", entry)
        thumbnail = _extract(r'<media:thumbnail url="(.*?)"', entry)

        if video_id and title:
            videos.append({
                "video_id": video_id,
                "title": title,
                "link": link or f"https://www.youtube.com/watch?v={video_id}",
                "author": author,
                "published": published,
                "thumbnail": thumbnail,
            })
    return videos


def _extract(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text)
    return m.group(1) if m else None


def build_embed(video: dict) -> discord.Embed:
    embed = discord.Embed(
        title=video["title"],
        url=video["link"],
        color=discord.Color.red(),
    )
    embed.set_author(name=video["author"] or "YouTube")
    if video.get("thumbnail"):
        embed.set_image(url=video["thumbnail"])
    if video.get("published"):
        try:
            dt = datetime.fromisoformat(video["published"].replace("Z", "+00:00"))
            embed.timestamp = dt
        except ValueError:
            pass
    embed.set_footer(text="New YouTube Upload")
    return embed


async def poll_loop(bot: discord.Client):
    """Background task: poll all subscribed channels and post new videos."""
    await bot.wait_until_ready()
    logger.info("Poller started (interval: %ds)", POLL_INTERVAL_SECONDS)

    async with aiohttp.ClientSession() as session:
        while not bot.is_closed():
            subscriptions = db.get_subscriptions()

            # Group by channel so we only fetch each RSS feed once
            channels: dict[str, list] = {}
            for sub in subscriptions:
                channels.setdefault(sub["yt_channel_id"], []).append(sub)

            for yt_channel_id, subs in channels.items():
                videos = await fetch_rss(yt_channel_id, session)
                for video in videos:
                    if db.is_seen(video["video_id"]):
                        continue

                    # Silently discard videos older than the backfill window so
                    # the bot doesn't flood channels with history on first run.
                    if video.get("published"):
                        try:
                            published = datetime.fromisoformat(video["published"].replace("Z", "+00:00"))
                            if datetime.now(timezone.utc) - published > BACKFILL_WINDOW:
                                db.mark_seen(video["video_id"], yt_channel_id)
                                continue
                        except ValueError:
                            pass

                    db.mark_seen(video["video_id"], yt_channel_id)
                    embed = build_embed(video)

                    for sub in subs:
                        channel = bot.get_channel(int(sub["discord_channel_id"]))
                        if channel is None:
                            logger.warning(
                                "Discord channel %s not found for sub id %s",
                                sub["discord_channel_id"], sub["id"]
                            )
                            continue
                        try:
                            await channel.send(
                                content=f"🎥 New video from **{video['author']}**!",
                                embed=embed,
                            )
                            logger.info("Posted %s to channel %s", video["video_id"], channel.id)
                        except discord.Forbidden:
                            logger.error("No permission to post in channel %s", channel.id)
                        except Exception as e:
                            logger.error("Failed to post video %s: %s", video["video_id"], e)

                # Small delay between channels to be polite to YouTube
                await asyncio.sleep(2)

            logger.info("Poll complete. Sleeping %ds.", POLL_INTERVAL_SECONDS)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
