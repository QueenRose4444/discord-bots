import discord
from discord.ext import tasks, commands
import datetime
import asyncio
import os
from dotenv import load_dotenv
import json
import matplotlib.pyplot as plt
import numpy as np

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

report_channel = None
send_reports = False

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
                online_times[user_id] = {'username': member.name, 'online_times': []}
            current_status = member.status
            if current_status == discord.Status.online:
                # User is online, record the time
                online_times[user_id]['online_times'].append(datetime.datetime.now().isoformat())
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
async def weeklyreport(interaction: discord.Interaction, channel: discord.TextChannel):
    global report_channel, send_reports
    report_channel = channel
    send_reports = True
    await interaction.response.send_message(f"Weekly reports will be sent to {channel.mention}.", ephemeral=True)
    bot.loop.create_task(generate_weekly_report())

@bot.tree.command()
async def stopweeklyreport(interaction: discord.Interaction):
    global send_reports
    send_reports = False
    await interaction.response.send_message("Stopped sending weekly reports.", ephemeral=True)

@bot.tree.command()
async def analyzetrends(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id not in online_times:
        await interaction.response.send_message("No data available for analysis.", ephemeral=True)
        return

    # Generate scatterplot of logins per day of the week
    logins_per_day = [0] * 7
    for time_str in online_times[user_id]['online_times']:
        time = datetime.datetime.fromisoformat(time_str)
        logins_per_day[time.weekday()] += 1

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    plt.scatter(days, logins_per_day)
    plt.xlabel('Day of the Week')
    plt.ylabel('Number of Logins')
    plt.title('Days online')
    plt.savefig('logins_per_day.png')
    plt.close()

    # Analyze time of day the user is most likely to be online
    times_of_day = [0] * 24
    for time_str in online_times[user_id]['online_times']:
        time = datetime.datetime.fromisoformat(time_str)
        times_of_day[time.hour] += 1

    # Convert hours to 12-hour format
    hours_12 = [(h % 12 if h % 12 != 0 else 12) for h in range(24)]
    am_pm = ['AM' if h < 12 else 'PM' for h in range(24)]
    labels = [f"{h}:00 {ap}" for h, ap in zip(hours_12, am_pm)]

    plt.scatter(range(24), times_of_day)
    plt.xlabel('Hour of Day')
    plt.ylabel('Number of Logins')
    plt.title('Time of Day Online')
    plt.xticks(range(24), labels, rotation=45)
    plt.tight_layout()
    plt.savefig('logins_per_hour.png')
    plt.close()

    # Send the images to the user
    with open('logins_per_day.png', 'rb') as f:
        day_image = discord.File(f)
        await interaction.user.send(file=day_image)
    with open('logins_per_hour.png', 'rb') as f:
        hour_image = discord.File(f)
        await interaction.user.send(file=hour_image)

    # Clean up the images
    os.remove('logins_per_day.png')
    os.remove('logins_per_hour.png')

async def generate_weekly_report():
    while send_reports:
        now = datetime.datetime.now()
        next_monday = now + datetime.timedelta(days=(7 - now.weekday()))
        next_monday_morning = datetime.datetime(next_monday.year, next_monday.month, next_monday.day, 0, 0, 0)
        await asyncio.sleep((next_monday_morning - now).total_seconds())

        if not send_reports or report_channel is None:
            continue

        report_message = "Weekly Online Report:\n"
        for user_id in tracked_users:
            if user_id in online_times:
                username = online_times[user_id].get('username', 'Unknown User')
                report_message += f"User {username} (ID: {user_id}) has been online {len(online_times[user_id]['online_times'])} times.\n"

        await report_channel.send(report_message)

def save_tracked_users():
    with open(tracked_users_file, 'w') as f:
        json.dump(tracked_users, f, indent=4)

def save_online_times():
    # Fetch user names and add them to the online_times data
    for user_id in tracked_users:
        if user_id not in online_times:
            continue
        user = bot.get_user(int(user_id))
        if user:
            online_times[user_id]['username'] = user.name
        else:
            # If the user is not found (e.g., if they left the server), remove their data
            del online_times[user_id]

    # Save the updated online_times data to the JSON file
    with open(online_times_file, 'w') as f:
        json.dump(online_times, f, indent=4)

# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))