import discord
from discord import app_commands
from discord.ext import tasks
from datetime import datetime
import pytz
import json
import os

# --- Keep-alive Flask server ---
from keep_alive import run
run()  # Start Flask server in background

# --- Token from environment variable ---
TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN is None:
    print("❌ ERROR: DISCORD_TOKEN not found in Environment Variables")
    exit(1)

SAVE_FILE = "timezones.json"

# --- Bot setup ---
intents = discord.Intents.default()
intents.members = True  # Needed to modify nicknames
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

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

# --- Slash command: set timezone ---
@tree.command(name="settimezone", description="Set your city/timezone")
async def settimezone(interaction: discord.Interaction, city: str):
    try:
        tz = None
        for zone in pytz.all_timezones:
            if city.replace(" ", "_").lower() in zone.lower():
                tz = pytz.timezone(zone)
                break

        if not tz:
            await interaction.response.send_message(
                "❌ Timezone not found. Example: Paris, Tokyo, New_York", ephemeral=True
            )
            return

        user_timezones[str(interaction.user.id)] = tz.zone
        save_timezones()

        if str(interaction.user.id) not in original_names:
            original_names[str(interaction.user.id)] = interaction.user.display_name

        await interaction.response.send_message(
            f"✅ Timezone saved for {interaction.user.mention}: {tz.zone}", ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(f"⚠️ Error: {e}", ephemeral=True)

# --- Slash command: unset timezone ---
@tree.command(name="unsettimezone", description="Remove your timezone")
async def unsettimezone(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    if uid in user_timezones:
        del user_timezones[uid]
        save_timezones()
        try:
            if uid in original_names:
                await interaction.user.edit(nick=original_names[uid])
                del original_names[uid]
        except Exception:
            pass
        await interaction.response.send_message(
            f"🗑️ Timezone removed for {interaction.user.mention}", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "⚠️ No timezone set.", ephemeral=True
        )

# --- Task: update nicknames every minute ---
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

                    # Keep full nickname
                    base_name = original_names.get(uid, member.name)

                    # Remove old timestamp if present
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
    await tree.sync()  # Sync slash commands with Discord

bot.run(TOKEN)
