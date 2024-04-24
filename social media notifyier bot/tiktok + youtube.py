import discord
from discord.ext import commands
import json
import time
import logging
import os
from dotenv import load_dotenv
from TikTokApi import TikTokApi
import googleapiclient.discovery  # For YouTube API
import asyncio

# Load environment variables from the .env file
load_dotenv()

# Access environment variables (replace with your actual keys/secrets)
BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
MS_TOKEN = os.getenv("MS_TOKEN")

# Data directory
DATA_DIR = "data"

# Logs directory
LOGS_DIR = "logs"

# Create data and logs directories if they don't exist
for directory in [DATA_DIR, LOGS_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Set up logging
logging.basicConfig(filename=os.path.join(LOGS_DIR, "bot.log"), level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_user_data_file(user_id):
    return os.path.join(DATA_DIR, str(user_id), "subscriptions.json")

def load_user_subscriptions(user_id):
    try:
        with open(get_user_data_file(user_id), "r") as f:
            data = json.load(f)
            return {platform: (usernames if isinstance(usernames, list) else []) for platform, usernames in data.items()} 
    except FileNotFoundError:
        return {}

def save_user_subscriptions(user_id, subscriptions):
    user_data_dir = os.path.join(DATA_DIR, str(user_id))
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
    with open(get_user_data_file(user_id), "w") as f:
        json.dump(subscriptions, f, indent=4)

# Function to fetch latest YouTube video ID
async def get_latest_youtube_video_id(username):
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    request = youtube.channels().list(part="contentDetails", forUsername=username)
    response = request.execute()
    if response.get("items"):
        uploads_playlist_id = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        request = youtube.playlistItems().list(part="snippet", playlistId=uploads_playlist_id, maxResults=1)
        response = request.execute()
        if response.get("items"):
            return response["items"][0]["snippet"]["resourceId"]["videoId"]
    return None

# Function to fetch latest TikTok video URL
async def get_latest_tiktok_video_url(username):
    user_videos = tiktok_api.by_username(username, count=1)
    if user_videos:
        return user_videos[0].as_dict.get("video", {}).get("playAddr")
    else:
        return None

async def check_for_new_videos(loop):
    while True:
        for user_id in os.listdir(DATA_DIR):
            user_id = int(user_id)
            subscriptions = load_user_subscriptions(user_id)
            for platform, usernames in subscriptions.items():
                for username in usernames:
                    try:
                        if platform.lower() == "youtube":
                            latest_video_id = await get_latest_youtube_video_id(username)
                            stored_video_id = subscriptions.get(platform, {}).get(username) 
                            if latest_video_id and latest_video_id != stored_video_id:
                                video_link = f"https://www.youtube.com/watch?v={latest_video_id}"
                                user = client.get_user(user_id)
                                loop.create_task(user.send(f"New video from {username} on YouTube: {video_link}")) 
                                subscriptions[platform][username] = latest_video_id  
                                save_user_subscriptions(user_id, subscriptions)
                        elif platform.lower() == "tiktok":
                            latest_video_url = await get_latest_tiktok_video_url(username)
                            stored_video_url = subscriptions.get(platform, {}).get(username)
                            if latest_video_url and latest_video_url != stored_video_url:
                                user = client.get_user(user_id)
                                loop.create_task(user.send(f"New video from {username} on TikTok: {latest_video_url}"))
                                subscriptions[platform][username] = latest_video_url 
                                save_user_subscriptions(user_id, subscriptions)
                    except Exception as e:
                        logging.error(f"Error checking for new videos for user {user_id}, username {username}: {e}")

        # Check for new videos every hour
        time.sleep(3600)

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.synced = False

    async def on_ready(self):
        global tiktok_api
        tiktok_api = TikTokApi()
        await tiktok_api.create_sessions(ms_tokens=[MS_TOKEN], num_sessions=1, sleep_after=3)
        await self.wait_until_ready()
        if not self.synced:
            await tree.sync()
            self.synced = True
        print(f"Logged in as {self.user}")
        self.loop.create_task(check_for_new_videos(self.loop))  # Moved this line here

async def main():
    global tiktok_api
    tiktok_api = TikTokApi()
    await tiktok_api.create_sessions(ms_tokens=[MS_TOKEN], num_sessions=1, sleep_after=3)

    client = MyClient()
    tree = app_commands.CommandTree(client)


    @client.tree.command(name="track", description="Track a new YouTube or TikTok account for video notifications.")
    @app_commands.describe(platform="The platform to track (YouTube or TikTok)", username="The username of the account to track")
    async def track(interaction: discord.Interaction, platform: str, username: str):
        subscriptions = load_user_subscriptions(interaction.user.id)
        if platform not in subscriptions:
            subscriptions[platform] = {}  # Use a dictionary to store username and video ID/URL
        subscriptions[platform][username] = None  # Initialize with None for video ID/URL 
        save_user_subscriptions(interaction.user.id, subscriptions)
        logging.info(f"{interaction.user} is now tracking {username} on {platform}")
        await interaction.response.send_message(f"Tracking new videos for {username} on {platform}")



    @client.tree.command(name="list", description="List your current subscriptions.")
    async def list(interaction: discord.Interaction):
        subscriptions = load_user_subscriptions(interaction.user.id)
        if subscriptions:
            message_text = "Your subscriptions:\n"
            for platform, usernames in subscriptions.items():
                message_text += f"**{platform.upper()}**: {', '.join(usernames.keys())}\n" 
        else:
            message_text = "You are not currently tracking any accounts."
        await interaction.response.send_message(message_text)



    @client.tree.command(name="untrack", description="Stop tracking a YouTube or TikTok account.")
    @app_commands.describe(platform="The platform to untrack (YouTube or TikTok)", username="The username of the account to stop tracking")
    async def untrack(interaction: discord.Interaction, platform: str, username: str):
        subscriptions = load_user_subscriptions(interaction.user.id)
        if platform in subscriptions and username in subscriptions[platform]:
            del subscriptions[platform][username]
            save_user_subscriptions(interaction.user.id, subscriptions)
            await interaction.response.send_message(f"You are no longer tracking {username} on {platform}.")
        else:
            await interaction.response.send_message(f"You were not tracking {username} on {platform}.")


    # Run the bot
    await client.start(BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())