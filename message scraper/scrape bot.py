import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the bot token and channel ID from the environment variables
TOKEN = os.getenv('DISCORD_TOKEN')

# Define the intents
intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent
intents.messages = True         # Enable the messages intent

# Create the bot with the specified intents
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    await bot.tree.sync()  

@bot.tree.command(name="scrape", description="Scrape messages from the current channel") 
async def scrape_command(interaction: discord.Interaction, limit: int = None):
    """Scrapes messages from the current channel with an optional limit."""
    channel = interaction.channel  
    user = interaction.user
    username = f"{user.name}#{user.discriminator}"
    channel_id = channel.id

    try:
        # Create the outputs directory if it doesn't exist
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, 'outputs')
        os.makedirs(output_dir, exist_ok=True)

        # Construct the output file name with channel ID and user ID
        output_file_name = f"{channel_id}_{username}.txt"
        output_file_path = os.path.join(output_dir, output_file_name)

        with open(output_file_path, 'w', encoding='utf-8') as file:
            async for message in channel.history(limit=limit):
                timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
                output_string = f'{message.author.name}: {timestamp}: {message.content}'
                print(output_string)
                file.write(output_string + '\n')

        # Send the file to the user
        with open(output_file_path, 'rb') as f:
            file_discord = discord.File(f, filename=output_file_name)
            await interaction.response.send_message(file=file_discord, ephemeral=True)

    except Exception as e:
        print(f"An error occurred: {e}")
        await interaction.response.send_message("An error occurred while scraping messages.", ephemeral=True)

bot.run(TOKEN)