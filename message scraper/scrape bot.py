import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

# Get the bot token from the environment variables
TOKEN = os.getenv('DISCORD_TOKEN')

# Define the intents
intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent

# Create the bot with the specified intents
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    await bot.tree.sync()  # Sync the application commands

@bot.tree.command(name="scrape", description="Scrape messages from the current channel")
async def scrape_command(interaction: discord.Interaction, limit: str = "all"):
    """Scrapes messages from the current channel with an optional limit."""
    channel = interaction.channel
    user = interaction.user
    username = user.name
    discriminator = user.discriminator
    channel_id = channel.id
    server_id = channel.guild.id
    current_time = datetime.now().strftime('%Y-%m-%d %H-%M-%S')

    try:
        # Create the outputs directory if it doesn't exist
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, 'outputs')
        os.makedirs(output_dir, exist_ok=True)

        # Construct the output file name with user details and server ID
        output_file_name = f"{username}#{discriminator}_{limit}_{current_time}_server-id-{server_id}.txt"
        output_file_path = os.path.join(output_dir, output_file_name)

        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write(f'Username: {username}#{discriminator}\n')
            file.write(f'Number of messages: {limit}\n')
            file.write(f'Date of command: {current_time}\n')
            file.write(f'Server ID: {server_id}\n')
            file.write('---\n')

            previous_author = None
            
            if limit.lower() == "all":
                async for message in channel.history(limit=None):
                    if previous_author and previous_author != message.author.name:
                        file.write('\n')  # Add an extra line between different users

                    timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    output_string = f'{message.author.name}: {timestamp}: {message.content}'
                    print(output_string)
                    file.write(output_string + '\n')
                    previous_author = message.author.name
            elif limit.lower() == "today":
                today = datetime.now().date()
                async for message in channel.history(limit=None):
                    if message.created_at.date() != today:
                        break
                    if previous_author and previous_author != message.author.name:
                        file.write('\n')  # Add an extra line between different users

                    timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    output_string = f'{message.author.name}: {timestamp}: {message.content}'
                    print(output_string)
                    file.write(output_string + '\n')
                    previous_author = message.author.name
            else:
                limit = int(limit)
                async for message in channel.history(limit=limit):
                    if previous_author and previous_author != message.author.name:
                        file.write('\n')  # Add an extra line between different users

                    timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    output_string = f'{message.author.name}: {timestamp}: {message.content}'
                    print(output_string)
                    file.write(output_string + '\n')
                    previous_author = message.author.name

        # Send the file to the user
        with open(output_file_path, 'rb') as f:
            file_discord = discord.File(f, filename=output_file_name)
            await interaction.response.send_message(file=file_discord, ephemeral=True)

    except Exception as e:
        print(f"An error occurred: {e}")
        await interaction.response.send_message("An error occurred while scraping messages.", ephemeral=True)

bot.run(TOKEN)