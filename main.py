import discord
from discord.ext import commands, tasks
from datetime import datetime
import pytz
import json
import os

# --- Keep-alive ---
from keep_alive import run
run()  # Démarre le serveur Flask en arrière-plan

# --- Read token from environment variable ---
TOKEN = os.environ.get("DISCORD_TOKEN")  # Set this in Render .env
if TOKEN is None:
    print("❌ ERROR: DISCORD_TOKEN not found in Environment Variables")
    exit(1)

SAVE_FILE = "timezones.json"

# --- Bot setup ---
intents = discord.Intents.default()
intents.members = True  # Needed to modify nicknames
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Load saved timezones ---
if os.path.exists(SAVE_FILE):
    with open(SAVE_FILE, "r") as f:
        user_timezones = json.load(f)
else:
    user_timezones = {}

# --- Store original full nicknames ---
original_names = {}

def save_timezones():
    with open(SAVE_FILE, "w") as f:
        json.dump(user_timezones, f)

# --- Command to set city/timezone ---
@bot.command()
async def settimezone(ctx, *, city: str):
    try:
        tz = None
        for zone in pytz.all_timezones:
            if city.replace(" ", "_").lower() in zone.lower():
                tz = pytz.timezone(zone)
                break

        if not tz:
            await ctx.send("❌ Timezone not found. Example: Paris, Tokyo, New_York")
            return

        user_timezones[str(ctx.author.id)] = tz.zone
        save_timezones()

        if str(ctx.author.id) not in original_names:
            original_names[str(ctx.author.id)] = ctx.author.display_name

        await ctx.send(f"✅ Timezone saved for {ctx.author.mention}: {tz.zone}")
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")

# --- Command to remove timezone ---
@bot.command()
async def unsettimezone(ctx):
    uid = str(ctx.author.id)
    if uid in user_timezones:
        del user_timezones[uid]
        save_timezones()
        try:
            if uid in original_names:
                await ctx.author.edit(nick=original_names[uid])
                del original_names[uid]
        except Exception:
            pass
        await ctx.send(f"🗑️ Timezone removed for {ctx.author.mention}")
    else:
        await ctx.send("⚠️ No timezone set.")

# --- Task to update nicknames every minute ---
@tasks.loop(minutes=1)
async def update_nicknames():
    for guild in bot.guilds:
        for member in guild.members:
            uid = str(member.id)
            if uid in user_timezones:
                try:
                    tz = pytz.timezone(user_timezones[uid])
                    now = datetime.now(tz)
                    time_str = now.strftime("%H:%M")

                    base_name = original_names.get(uid, member.name)

                    if "[" in base_name and "]" in base_name:
                        base_name = base_name.split("[")[0].strip()

                    new_nick = f"{base_name} [{time_str}]"
                    if member.display_name != new_nick:
                        await member.edit(nick=new_nick)
                except discord.Forbidden:
                    pass
                except Exception:
                    pass

@bot.event
async def on_ready():
    print(f"✅ Connected as {bot.user}")
    update_nicknames.start()

bot.run(TOKEN)
