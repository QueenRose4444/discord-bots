import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import urllib.parse
import json

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Get the script's directory and create the output base directory
script_dir = os.path.dirname(os.path.abspath(__file__))
output_base_dir = os.path.join(script_dir, "outputs")

# Load or initialize scrape status
scrape_status_file = os.path.join(output_base_dir, "scrape_status.json")
if os.path.exists(scrape_status_file):
    with open(scrape_status_file, "r") as f:
        scrape_status = json.load(f)
else:
    scrape_status = {}

message_edit_counts = {}

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


async def log_message(message, edit_count=None, is_edit=False):
    if message.author.bot:
        return

    server_dir = os.path.join(output_base_dir, f"{message.guild.name}_{message.guild.id}")
    channel_dir = os.path.join(server_dir, f"{message.channel.name}_{message.channel.id}")
    os.makedirs(server_dir, exist_ok=True)
    os.makedirs(channel_dir, exist_ok=True)
    output_file = os.path.join(channel_dir, "messages.txt")

    with open(output_file, "a", encoding="utf-8") as f:
        if is_edit:
            timestamp = message.edited_at.strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"    Edit {edit_count}: {timestamp}: {message.content}\n")  # Indent edits
        else:
            timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{message.author.name}: {timestamp}: {message.content}\n")

            for attachment in message.attachments:
                relative_path = await download_attachment(attachment, channel_dir)
                if relative_path:
                    file_path = os.path.abspath(os.path.join(channel_dir, relative_path))
                    encoded_file_path = urllib.parse.quote(file_path)
                    if attachment.content_type and attachment.content_type.startswith("image/"):
                        f.write(f"Attachment: ![{attachment.filename}](file://{encoded_file_path})\n")
                    else:
                        f.write(f"Attachment: <{attachment.url}>\n")


async def scrape_channel(channel):
    server_dir = os.path.join(output_base_dir, f"{channel.guild.name}_{channel.guild.id}")
    channel_dir = os.path.join(server_dir, f"{channel.name}_{channel.id}")
    os.makedirs(server_dir, exist_ok=True)
    os.makedirs(channel_dir, exist_ok=True)
    output_file = os.path.join(channel_dir, "messages.txt")

    try:
        last_message_id = scrape_status.get(str(channel.id))

        with open(output_file, "a", encoding="utf-8") as f:
            if last_message_id:
                async for message in channel.history(limit=None, after=discord.Object(id=last_message_id), oldest_first=True):
                    timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"{message.author.name}: {timestamp}: {message.content}\n")
                    # ... (Handle attachments - same logic as in log_message)

            else:
                async for message in channel.history(limit=None, oldest_first=True):
                    timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"{message.author.name}: {timestamp}: {message.content}\n")
                    # ... (Handle attachments - same logic as in log_message)


            if messages := [message async for message in channel.history(limit=1)]:
                scrape_status[str(channel.id)] = messages[0].id
                with open(scrape_status_file, "w") as status_file:
                    json.dump(scrape_status, status_file, indent=4)


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

@bot.event
async def on_message_edit(before, after):
    message_id = str(after.id)

    if message_id not in message_edit_counts:
        message_edit_counts[message_id] = 1  # Start counting edits for this message ID
    else:
        message_edit_counts[message_id] += 1

    await log_message(after, edit_count=message_edit_counts[message_id], is_edit=True)


bot.run(TOKEN)