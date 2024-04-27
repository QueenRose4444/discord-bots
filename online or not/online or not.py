import discord
import os
import datetime
import calendar
from dotenv import load_dotenv

load_dotenv()

# Define the intents
intents = discord.Intents.default()
intents.members = True

# Create the client with the specified intents
client = discord.Client(intents=intents)

# Replace these IDs with the IDs of the users you want to monitor
monitored_user_ids = [1051742499472932894, 436471690621353999, 411000471776657419, 212139958662725642]

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_member_update(before, after):
    # Check if the updated member is one of the monitored users
    if after.id in monitored_user_ids:
        if str(before.status) == "offline" and str(after.status) == "online":
            print(f"{after.name} is now online at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            # Store online time in a file
            store_status_time(after.id, "online")
        elif str(before.status) == "online" and str(after.status) == "offline":
            print(f"{after.name} is now offline at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            # Store offline time in a file
            store_status_time(after.id, "offline")


# Function to store the status and time in a file
def store_status_time(user_id, status):
    # Get the current date and week number
    today = datetime.date.today()
    week_number = today.isocalendar()[1]

    # Create the directory structure if it doesn't exist
    if not os.path.exists("online_offline_data"):
        os.mkdir("online_offline_data")

    year_dir = f"online_offline_data/{today.year}"
    if not os.path.exists(year_dir):
        os.mkdir(year_dir)

    # Open the file for the current week
    file_name = f"{year_dir}/week{week_number}.txt"
    with open(file_name, "a") as f:
        f.write(f"{user_id} is {status} at {today.strftime('%Y-%m-%d')} {datetime.datetime.now().strftime('%H:%M:%S')}\n")

# Function to check if it's a new week
def is_new_week(last_checked_date):
    today = datetime.date.today()
    last_checked_week = last_checked_date.isocalendar()[1]
    current_week = today.isocalendar()[1]
    return last_checked_week != current_week

# Function to create a new file for the new week
def create_new_week_file(last_checked_date):
    today = datetime.date.today()
    week_number = today.isocalendar()[1]
    year_dir = f"online_offline_data/{today.year}"

    # Open the file for the new week
    file_name = f"{year_dir}/week{week_number}.txt"
    with open(file_name, "w") as f:
        f.write(f"Week {week_number} - {calendar.month_name[today.month]} {today.day}, {today.year}\n")

    return today

# Get the token from the DISCORD_BOT_TOKEN environment variable
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
client.run(TOKEN)

