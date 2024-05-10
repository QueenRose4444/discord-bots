import discord
from discord.ext import tasks, commands
import datetime
import asyncio
import os
from dotenv import load_dotenv
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Load environment variables from .env file
load_dotenv()

intents = discord.Intents.default()
intents.presences = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Get the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the file paths for tracked_users and online_times
tracked_users_file = os.path.join(script_dir, 'tracked_users.json')
online_times_file = os.path.join(script_dir, 'online_times.json')

# Initialize tracked_users and online_times from existing data or empty structures
try:
    with open(tracked_users_file, 'r') as f:
        tracked_users = json.load(f)
except FileNotFoundError:
    tracked_users = []

try:
    with open(online_times_file, 'r') as f:
        online_times = json.load(f)
except FileNotFoundError:
    online_times = {}

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    track_online_times.start()
    await bot.tree.sync()  # Sync the application commands

@tasks.loop(minutes=1)
async def track_online_times():
    for member in bot.get_all_members():
        user_id = str(member.id)
        if user_id in tracked_users:
            # Check if the user's status has changed
            if user_id not in online_times:
                online_times[user_id] = {'username': member.name, 'sessions': []}

            current_status = member.status
            if current_status == discord.Status.online:
                # User is online, start a new session if not already in one
                if 'current_session' not in online_times[user_id]:
                    online_times[user_id]['current_session'] = {'start_time': datetime.datetime.now().isoformat()}
            else:
                # User is offline, end the current session if there is one
                if 'current_session' in online_times[user_id]:
                    end_time = datetime.datetime.now()
                    start_time = datetime.datetime.fromisoformat(online_times[user_id]['current_session']['start_time'])
                    duration = (end_time - start_time).total_seconds() / 60  # Duration in minutes
                    del online_times[user_id]['current_session']
                    online_times[user_id]['sessions'].append({
                        'start_time': start_time.isoformat(),
                        'duration': duration
                    })
    save_online_times()  # Save the online times to the JSON file

@track_online_times.before_loop
async def before_track_online_times():
    await bot.wait_until_ready()

@bot.tree.command()
async def optin(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id not in tracked_users:
        tracked_users.append(user_id)
        save_tracked_users()
        await interaction.response.send_message("You are now opted in to being tracked.", ephemeral=True)
    else:
        await interaction.response.send_message("You are already opted in to being tracked.", ephemeral=True)

@bot.tree.command()
async def analyzedata(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id not in online_times or 'sessions' not in online_times[user_id]:
        await interaction.response.send_message("No data available for analysis.", ephemeral=True)
        return

    # Extract session data
    sessions = online_times[user_id]['sessions']
    start_times = [datetime.datetime.fromisoformat(session['start_time']) for session in sessions]
    durations = [session['duration'] for session in sessions]

    # Plot session durations over time
    plt.figure(figsize=(10, 5))
    plt.plot_date(start_times, durations, 'o-')
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.gcf().autofmt_xdate()
    plt.xlabel('Time of Day')
    plt.ylabel('Session Duration (minutes)')
    plt.title('Time Spent Online Over Time')
    plt.savefig('time_spent_online.png')
    plt.close()

    # Send the image to the user
    with open('time_spent_online.png', 'rb') as f:
        image_file = discord.File(f)
        await interaction.user.send(file=image_file)

    # Clean up the image
    os.remove('time_spent_online.png')

def save_tracked_users():
    with open(tracked_users_file, 'w') as f:
        json.dump(tracked_users, f, indent=4)

def save_online_times():
    # Save the updated online_times data to the JSON file
    with open(online_times_file, 'w') as f:
        json.dump(online_times, f, indent=4)

# Run the bot
bot.run(os.getenv("DISCORD_BOT_TOKEN"))