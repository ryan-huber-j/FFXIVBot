# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import os
import random

import discord
import requests
import sqlite3
from discord.ext import commands
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


@bot.event
async def on_member_join(member):
    await member.create_dm()
    await member.dm_channel.send(
        f'Hi {member.name}, welcome to {member.guild.name}!'
    )


@bot.command(name='welcome_me', help='Test')
async def on_member_join(ctx):
    await ctx.author.create_dm()
    await ctx.author.dm_channel.send(
        f'Hi {ctx.author.name}, welcome to {ctx.author.guild.name}!'
    )


@bot.command(name='my_ign_is')
async def nickname_set(ctx, name):
    await ctx.author.edit(nick=name)


@bot.command(name='me_so_hungy')
async def feed(ctx):
    data = get_data(ctx)
    set_data(ctx, 'cookie_count', int(data[0][2]) + 1)
    await ctx.send(f'Here, {ctx.author.name} have a cookie 🍪')


@bot.command(name='count_cookies')
async def count_cookies(ctx):
    data = get_data(ctx)
    await ctx.send(f'You have eaten {data[0][2]} cookies')


@bot.command(name='99', help='Responds with a random quote from Brooklyn 99')
async def nine_nine(ctx):
    print('xxx')
    brooklyn_99_quotes = [
        'I\'m the human form of the 💯 emoji.',
        'Bingpot!',
        (
            'Cool. Cool cool cool cool cool cool cool, '
            'no doubt no doubt no doubt no doubt.'
        ),
    ]

    response = random.choice(brooklyn_99_quotes)
    await ctx.send(response)


@bot.command(name='roll_dice', help='Simulates rolling dice.')
async def roll(ctx, number_of_dice: int, number_of_sides: int):
    dice = [
        str(random.choice(range(1, number_of_sides + 1)))
        for _ in range(number_of_dice)
    ]
    await ctx.send(', '.join(dice))


@bot.command(name='ss', help='Provides character screenshot')
async def ss(ctx, world=None, character=None):
    if world is not None:
        print("https://ffxiv-character-cards.herokuapp.com/characters/name/" + world + "/" + character + ".png")
        response = requests.get(
            "https://ffxiv-character-cards.herokuapp.com/characters/name/" + world + "/" + character + ".png")
    else:
        data = get_data(ctx)
        if len(data) == 0:
            await ctx.send("I do not know who you are. Please enter your lodestone ID using the command: \"i_am {"
                           "lodestone ID}")
        print("https://ffxiv-character-cards.herokuapp.com/characters/id/" + str(data[0][1]) + ".png")
        response = requests.get("https://ffxiv-character-cards.herokuapp.com/characters/id/" + str(data[0][1]) + ".png")
    if response.status_code != 200:
        await ctx.send('Failed to create character card')
        return
    file = open("webpage.png", "wb")
    file.write(response.content)
    file.close()
    await ctx.send(file=discord.File("webpage.png"))


@bot.command(name='i_am', help='Stores character lodestone ID', pass_context=True)
async def i_am(ctx, ld_id):
    data = get_data(ctx)
    if data[0][1] is None or not ld_id == str(data[0][1]):
        set_data(ctx, 'ld_id', ld_id)
        data = get_data(ctx)
        await ctx.send('I have registered you as: ' + str(data[0][1]))
    else:
        await ctx.send('I already know who you are, ' + str(data[0][1]))


@bot.command(name="who_am_i", help='Retrieves stored lodestone ID')
async def who_am_i(ctx):
    data = get_data(ctx)
    if data[0][1] is None:
        await ctx.send('I do not know who you are')
    else:
        await ctx.send('You are ' + str(data[0][1]))


@bot.command(name="get_results", help="Retrieves participant GC ranking results")
async def get_results(ctx):
    await ctx.message.delete()
    channel = bot.get_channel(954126336228720701)
    message = await channel.history().find(lambda m: 954140685592846387 in m.raw_role_mentions)
    if message is None:
        return
    fcm = set()
    for mem in requests.get("https://xivapi.com/freecompany/9231394073691073564?data=FCM").json()["FreeCompanyMembers"]:
        fcm.add(str(mem["ID"]))
    participants = {}
    coaches = {}
    for reaction in message.reactions:
        async for user in reaction.users():
            if reaction.emoji == "🇵":
                participants[ctx.guild.get_member(user.id).display_name] = "false"
            if reaction.emoji == "🇨":
                coaches[ctx.guild.get_member(user.id).display_name] = "false"
    results = {}
    msg = None
    first_hit = True
    for x in range(1, 6):
        await getResultsOnPage(results, x, fcm, participants, coaches, first_hit)
        if msg:
            await msg.delete()
        msg = await ctx.send(f"{20 * x}% complete")
    if msg:
        await msg.delete()
    participant_list = "\n".join(["\n".join(user[1:] for user in results if user.startswith('p')),
                                  "\n".join(f"Rank ???: {user} - **???**" for user in participants if participants[user] == "false" and user not in coaches)])
    coach_list = "\n".join(["\n".join(user[1:] for user in results if user.startswith('c')),
                            "\n".join(f"Rank ???: *{user}* - **???**" for user in coaches if coaches[user] == "false")])
    other_list = "\n".join(user[1:] for user in results if user.startswith('x'))
    await ctx.send("\n".join(["✅ Participants\nNote: "
                              "Italicized means that the participant was a coach, not competing for contest prizes."
                              " Ranks Labeled \"???\" were less than the server-wide top 500 or unlisted at all.\n",
                              participant_list.strip(), "\n🛂 Coaches", coach_list.strip(), "\n⚠ Honorable Mentions",
                              other_list.strip()]))


async def getResultsOnPage(results, x, fcm, participants, coaches, first_hit):
    soup = BeautifulSoup(requests.get(f"https://na.finalfantasyxiv.com/lodestone/ranking/gc/weekly/?page={x}&filter=1"
                                      "&worldname=Siren").content, 'html.parser')
    ranked_peeps = soup.select("tbody tr")
    for result in ranked_peeps:
        player_id = str(result["data-href"]).split("/")[3]
        if player_id in fcm:
            score = str(result.find("td", {"class": "ranking-character__value"}).text).strip()
            name = str(result.find("h4").contents[0]).strip()
            ranking = str(result.select(".ranking-character__number")[0].text).strip()
            designation = "x"
            it = ""
            win = ""
            if name in participants and name not in coaches:
                designation = "p"
                participants[name] = "true"
                if first_hit:
                    win = "WINNER"
                    first_hit = False
            if name in coaches:
                designation = "c"
                coaches[name] = "true"
                it = "*"
            results[f"{designation}Rank {ranking}: {it}{name}{it} - **{score}** {win}"] = None


def get_data(ctx):
    # define database
    conn = sqlite3.connect("bot")
    cursor = conn.cursor()
    # get stored object from database
    sql = "SELECT * FROM bot WHERE d_id=?"
    cursor.execute(sql, [ctx.author.id])
    data = cursor.fetchall()
    if len(data) == 0:
        cursor.execute('INSERT INTO bot (d_id) VALUES (?)', [ctx.author.id])
        cursor.execute(sql, [ctx.author.id])
        data = cursor.fetchall()
    # close database connection
    conn.commit()
    conn.close()
    return data


def set_data(ctx, key, value):
    conn = sqlite3.connect("bot")
    cursor = conn.cursor()
    sql = "SELECT * FROM bot WHERE d_id=?"
    cursor.execute(sql, [ctx.author.id])
    data = cursor.fetchall()
    # if object does not exist, create it
    if len(data) == 0:
        sql = "INSERT INTO bot (d_id) VALUES (?)"
        cursor.execute(sql, [ctx.message.author.id])
    else:
        sql = f'UPDATE bot SET {key} = ? WHERE d_id = ?'
        cursor.execute(sql, [value, ctx.author.id])
    conn.commit()
    conn.close()


bot.run(TOKEN)
