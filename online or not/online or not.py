import discord
import os

client = discord.Client()

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_member_update(before, after):
    if str(before.status) == "offline" and str(after.status) == "online":
        print(f"{after.name} is now online.")
    elif str(before.status) == "online" and str(after.status) == "offline":
        print(f"{after.name} is now offline.")

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
client.run(TOKEN)
