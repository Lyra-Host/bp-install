import discord
from discord.ext import commands, tasks
import os
import sys

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    print(f"Loading cogs...")
    
    await bot.load_extension("cogs.blueprint_installer")
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    print(f"[v0] Bot is ready!")

if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    
    if not token:
        print("❌ DISCORD_BOT_TOKEN environment variable is required!")
        sys.exit(1)
    
    bot.run(token)
