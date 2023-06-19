#!/usr/bin/env python3

import discord
from discord.ext import commands
from discord import app_commands
import interactions
import random

intents = discord.Intents.all()
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

interact = None
ran = False

members = {}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

def shuffled_dict(d:dict):
    return {k: d[k] for k in random.sample(d.keys(), len(d))}

# Register the balance command
async def balance(ctx):
    global interact
    global ran

    interact = ctx
    total_threshold = 1000
    average_threshold = 1000
    channel = discord.utils.get(ctx.guild.channels, name='lobby')
    members = random.sample(channel.members, len(channel.members))  # Shuffle members
    msg_channel = ctx.channel
    msg = ""
    print("success")
    if len(members) < 2 or len(members) > 10:
        await ctx.response.send_message("How the heck am I suppose to balance " + str(len(members)) + "? Math ain't mathin.")
        return

    roles_data = {}
    total_elo = 0
    member_count = 0
    role_elo = {
        'bronze': 1000,
        'silver': 1500,
        'gold': 2000,
        'platinum': 2500,
        'diamond': 3000,
        'master': 3500,
        'grandmaster': 4000
    }

    for member in members:
        member_elo = 0
        for role in member.roles:
            role_name = role.name.lower()
            if role_name in role_elo.keys():
                member_count = member_count + 1
                member_elo = role_elo[role_name]
                roles_data[member] = member_elo
                total_elo += member_elo
                break

    if member_count < 2 or member_count > 10:
        await ctx.response.send("How the heck am I suppose to balance " + str(member_count) + "? Math ain't mathin.")
        return

    average_elo = total_elo / len(roles_data)
    
    balance = False

    temp_msg = await msg_channel.send("Balancing teams with my big ole Kaplan brain.")

    attempts = 0

    if ran is False:
        await ctx.response.send_message(f"Get Kap'd on\n\n")

    while (balance == False):
        roles_data = shuffled_dict(roles_data)
        attempts = attempts + 1
        teams = {'team1': [], 'team2': []}
        team1_elo = 0
        team2_elo = 0

        for member, elo in roles_data.items():
            if team1_elo <= team2_elo and len(teams['team1']) <= 5:
                teams['team1'].append(member)
                team1_elo += elo
            elif team2_elo <= team1_elo:
                teams['team2'].append(member)
                team2_elo += elo

        # Calculate average ELO for each team
        average_team1 = team1_elo / len(teams['team1'])
        average_team2 = team2_elo / len(teams['team2'])

        # Calculate average ELO for all players
        average_all_players = total_elo / len(roles_data)
        
        if abs(average_team1 - average_team2) <= average_threshold and abs(team1_elo - team2_elo) <= total_threshold:
            await msg_channel.delete_messages([temp_msg])
            balance = True

        if attempts == 100:
            await msg_channel.delete_messages([temp_msg])
            msg += f"Shits takin too long, try these teams idk.\n\n"
            balance = True

    # Send a message with the team balancing results
    msg +=  f"Teams have been balanced!\n\n"
    msg += f"Lobby Average Elo: {round(average_elo)}\n\n"
    msg += f"Team 1\n"
    msg += f"Average Elo: {round(average_team1)}\n"
    msg += f"Total Elo: {team1_elo}\n"
    for member in teams['team1']:
        msg += f"\t{member.name}\n"
    msg += f"\n"
    msg += f"Team 2\n"
    msg += f"Average Elo: {round(average_team2)}\n"
    msg += f"Total Elo: {team2_elo}\n"
    for member in teams['team2']:
        msg += f"\t{member.name}\n"
    msg += f"\n"
    msg += f"Click the 👍 reaction to move to voice channels, 👎 to redo the balancing, 🔄 to send back to lobby, or ❌ to cancel the bot." 

    message = await msg_channel.send(msg)

    await message.add_reaction("👍")
    await message.add_reaction("👎")
    await message.add_reaction("❌")

    # Store the teams and voice channels in a global variable for access in on_reaction_add
    bot.teams = teams
    bot.team1_vc = discord.utils.get(ctx.guild.voice_channels, name='team-1')
    bot.team2_vc = discord.utils.get(ctx.guild.voice_channels, name='team-2')
    bot.lobby_vc = discord.utils.get(ctx.guild.voice_channels, name='lobby')
    bot.balance_message = message

    ran = True

# Register the balance command as an application command
@bot.tree.command(name="balance", description="Going to balance the teams. Pretty self-explanatory")
async def balanceSlash(ctx: interactions):
    await balance(ctx)
    ctx.response

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:
        return
    
    global interact

    message = reaction.message
    guild = message.guild
    ctx = await bot.get_context(message)

    if reaction.message.author == bot.user and reaction.message == bot.balance_message:
        if str(reaction.emoji) == "👍":
            # Move members to their respective voice channels
            for member in bot.teams['team1']:
                await member.move_to(bot.team1_vc)

            for member in bot.teams['team2']:
                await member.move_to(bot.team2_vc)

            # Remove the user's reaction
            await reaction.remove(user)

            # Add a reaction to move everyone back to the lobby
            await reaction.message.add_reaction("🔄")
        elif str(reaction.emoji) == "👎":
            await bot.balance_message.delete()

            # Rebalance the teams.
            # balance_command = bot.slash_commands.get('balance')
            await balance(interact)
            # Remove the user's reaction
            # await reaction.remove(user)

    if reaction.message.author == bot.user and reaction.message == bot.balance_message and str(reaction.emoji) == "🔄":
        # Move everyone back to the lobby
        for member in bot.team1_vc.members:
            await member.move_to(bot.lobby_vc)

        for member in bot.team2_vc.members:
            await member.move_to(bot.lobby_vc)

        # Remove the user's reaction
        await reaction.remove(user)

    if reaction.message.author == bot.user and reaction.message == bot.balance_message and str(reaction.emoji) == "❌":
        await bot.balance_message.delete()

bot.run('TOKEN HERE')
