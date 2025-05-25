import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Get the script's directory and create the output base directory
script_dir = os.path.dirname(os.path.abspath(__file__))
output_base_dir = os.path.join(script_dir, "outputs")

async def download_attachment(attachment, channel_dir):
    attachments_dir = os.path.join(channel_dir, "attachments")
    os.makedirs(attachments_dir, exist_ok=True)
    try:
        file_path = os.path.join(attachments_dir, attachment.filename)
        await attachment.save(file_path)
        return os.path.relpath(file_path, channel_dir)
    except Exception as e:
        print(f"Error saving attachment: {e}")
        return None


async def log_message(message):
    if message.author.bot:
        return
    
    server_dir = os.path.join(output_base_dir, f"{message.guild.name}_{message.guild.id}")
    channel_dir = os.path.join(server_dir, f"{message.channel.name}_{message.channel.id}")
    os.makedirs(server_dir, exist_ok=True)
    os.makedirs(channel_dir, exist_ok=True)
    output_file = os.path.join(channel_dir, "messages.txt")

    with open(output_file, "a", encoding="utf-8") as f:
        timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"{message.author.name}: {timestamp}: {message.content}\n")

        for attachment in message.attachments:
            relative_path = await download_attachment(attachment, channel_dir)
            if relative_path:
                f.write(f"Attachment: {relative_path}\n")



async def scrape_channel(channel):
    server_dir = os.path.join(output_base_dir, f"{channel.guild.name}_{channel.guild.id}")
    channel_dir = os.path.join(server_dir, f"{channel.name}_{channel.id}")
    os.makedirs(server_dir, exist_ok=True)
    os.makedirs(channel_dir, exist_ok=True)
    output_file = os.path.join(channel_dir, "messages.txt")

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            async for message in channel.history(limit=None, oldest_first=True):
                timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{message.author.name}: {timestamp}: {message.content}\n")
                for attachment in message.attachments:
                    relative_path = await download_attachment(attachment, channel_dir)
                    if relative_path:
                        f.write(f"Attachment: {relative_path}\n")

    except discord.errors.Forbidden:
        print(f"Missing permissions to scrape {channel.name} in {channel.guild.name}")



@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await bot.tree.sync()

    os.makedirs(output_base_dir, exist_ok=True)

    print("Starting initial scrape...")
    for guild in bot.guilds:
        for channel in guild.text_channels:
            await scrape_channel(channel)
    print("Initial scrape complete.")



@bot.event
async def on_message(message):
    await log_message(message)
    await bot.process_commands(message)



bot.run(TOKEN)