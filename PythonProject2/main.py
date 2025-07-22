import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.dm_messages = True

bot = commands.Bot(command_prefix='/', intents=intents)

scheduled_events = []

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    check_events.start()

@bot.command()
async def schedule(ctx, date: str, time: str):
    """Schedule a game. Usage: /schedule YYYY-MM-DD HH:MM (UTC)"""
    try:
        dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        dt = pytz.utc.localize(dt)
        scheduled_events.append({
            "channel_id": ctx.channel.id,
            "author_id": ctx.author.id,
            "participants": [ctx.author.id],
            "datetime": dt,
            "notified_30min": False,
            "notified_start": False
        })
        await ctx.send(f"✅ Game scheduled for {dt.strftime('%Y-%m-%d %H:%M UTC')}.\nOthers can join with `/join`.")
    except ValueError:
        await ctx.send("⚠️ Invalid format. Use `/schedule YYYY-MM-DD HH:MM` (24h UTC).")

@bot.command()
async def join(ctx):
    upcoming = [e for e in scheduled_events if e["datetime"] > datetime.utcnow().replace(tzinfo=pytz.utc)]
    if not upcoming:
        await ctx.send("❌ No upcoming games to join.")
        return
    next_game = min(upcoming, key=lambda x: x["datetime"])
    if ctx.author.id not in next_game["participants"]:
        next_game["participants"].append(ctx.author.id)
        await ctx.send(f"✅ You’ve joined the game at {next_game['datetime'].strftime('%Y-%m-%d %H:%M UTC')}")
    else:
        await ctx.send("ℹ️ You’re already in the game.")

@tasks.loop(minutes=1)
async def check_events():
    now = datetime.utcnow().replace(tzinfo=pytz.utc)
    to_remove = []

    for event in scheduled_events:
        # 30-minute reminder
        if not event.get("notified_30min") and timedelta(minutes=29) < (event["datetime"] - now) <= timedelta(minutes=30):
            for user_id in event["participants"]:
                user = await bot.fetch_user(user_id)
                try:
                    await user.send(f"⏰ Reminder: Your football game starts in **30 minutes** at {event['datetime'].strftime('%Y-%m-%d %H:%M UTC')}!")
                except Exception as e:
                    print(f"Failed to send 30-min DM to {user_id}: {e}")
            event["notified_30min"] = True

        # Kickoff reminder
        if not event.get("notified_start") and now >= event["datetime"] and now < event["datetime"] + timedelta(minutes=1):
            for user_id in event["participants"]:
                user = await bot.fetch_user(user_id)
                try:
                    await user.send(f"🚨 Kickoff time! Your football game is starting **now** ({event['datetime'].strftime('%Y-%m-%d %H:%M UTC')})!")
                except Exception as e:
                    print(f"Failed to send kickoff DM to {user_id}: {e}")
            event["notified_start"] = True

        # Remove event 5 mins after start
        if now > event["datetime"] + timedelta(minutes=5):
            to_remove.append(event)

    for event in to_remove:
        scheduled_events.remove(event)



