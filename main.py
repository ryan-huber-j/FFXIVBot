import os
import random
import string

import discord
import requests
import sqlite3
from discord.ext import commands
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from typing import NamedTuple
from datetime import date

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='&', intents=intents)


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


@bot.command(name='me_so_hungy', help='Gives member a cookie')
async def feed(ctx):
    data = get_data(ctx)
    today = date.today().strftime("%Y-%m-%d")
    if data[0][3] != today:
        set_data(ctx, 'cookie_count', int(data[0][2]) + 1)
        set_data(ctx, 'last_cookie_date', today)
        await ctx.send(f'Here, {ctx.author.display_name}, have a cookie 🍪')
    else:
        await ctx.send(f'You already had a cookie today, {ctx.author.display_name}')


@bot.command(name='count_cookies', help='Returns member\'s cookie count')
async def count_cookies(ctx):
    data = get_data(ctx)
    await ctx.send(f'You have eaten {data[0][2]} cookies')


@bot.command(name='roll_dice', help='Simulates rolling dice.')
async def roll(ctx, number_of_dice: int, number_of_sides: int):
    dice = [
        str(random.choice(range(1, number_of_sides + 1)))
        for _ in range(number_of_dice)
    ]
    await ctx.send(', '.join(dice))


@bot.command(name='ss', help='Provides character screenshot')
async def ss(ctx, world=None, character=None):
    await ctx.message.delete()
    if world is not None:
        print("https://ffxiv-character-cards.herokuapp.com/characters/name/" + world + "/" + character + ".png")
        response = requests.get(
            "https://ffxiv-character-cards.herokuapp.com/characters/name/" + world + "/" + character + ".png")
    else:
        data = get_data(ctx)
        if len(data) == 0 or data[0][1] is None:
            await ctx.send("I do not know who you are. Please enter your lodestone ID using the command: \"i_am {"
                           "lodestone ID}")
            return
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
    await ctx.message.delete()
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


@bot.command(name="get_results", help="Retrieves all FC members' weekly GC ranking results")
async def get_results(ctx):
    await ctx.message.delete()
    channel = discord.utils.get(ctx.guild.channels, name='professionals-signups')
    if channel is None:
        await ctx.send("no channel named *professionals-signups* exists")
        return
    role = discord.utils.get(ctx.guild.roles, name="Professional")
    if role is None:
        await ctx.send("no role named *Professional* in channel named *professionals-signups*")
        return
    messages = [message async for message in channel.history(limit=100, oldest_first=False)]
    message = None
    for m in messages:
        if role.id in m.raw_role_mentions:
            message = m
            break
    if message is None:
        await ctx.send("no role named *Professional* mentioned in channel named *professionals-signups*")
        return
    fcm = set()
    for mem in requests.get("https://xivapi.com/freecompany/9231394073691073564?data=FCM").json()["FreeCompanyMembers"]:
        fcm.add(int(mem["ID"]))
    participants = {}
    coaches = {}
    for reaction in message.reactions:
        async for user in reaction.users():
            if reaction.emoji == "🇵":
                participants[str(ctx.guild.get_member(user.id).display_name).lstrip(string.punctuation + string.whitespace)] = "false"
            if reaction.emoji == "🇨":
                coaches[str(ctx.guild.get_member(user.id).display_name).lstrip(string.punctuation + string.whitespace)] = "false"
    results = {}
    msg = None
    for x in range(1, 6):
        await getResultsOnPage(results, x, fcm, participants, coaches)
        if msg:
            await msg.delete()
        msg = await ctx.send(f"{20 * x}% complete")
    if msg:
        await msg.delete()
    markWinner(results)
    participant_list = "\n".join(["\n".join(getScoreString(user) for user in results.values() if user.designation == "p"),
                                  "\n".join(f"Rank ???: {user} - **???**" for user in participants if participants[user] == "false" and user not in coaches)])
    coach_list = "\n".join(["\n".join(getScoreString(user) for user in results.values() if user.designation == "c"),
                            "\n".join(f"Rank ???: *{user}* - **???**" for user in coaches if coaches[user] == "false")])
    other_list = "\n".join(getScoreString(user) for user in results.values() if user.designation == "x")
    await ctx.send("\n".join(["✅ Participants\nNote: "
                              "Italicized means that the participant was a coach, not competing for contest prizes."
                              " Ranks Labeled \"???\" were less than the server-wide top 500 or unlisted at all.\n",
                              participant_list.strip(), "\n🛂 Coaches", coach_list.strip(), "\n⚠ Honorable Mentions\n"
                              "These were people who were non-participants but made it to top 500 and were in our FC!",
                              other_list.strip()]))


def getScoreString(scorer):
    if scorer.duplicate:
        explanation_of_duplication = " *Note: Defaulted to highest rank listed and combined score between two ranks earned*"
    else:
        explanation_of_duplication = ""
    if scorer.winner:
        win = " WINNER"
    else:
        win = ""
    if scorer.designation == "c":
        it = "*"
    else:
        it = ""
    return f"Rank {scorer.ranking}: {it}{scorer.name}{it} - **{scorer.score:,}**{win}{explanation_of_duplication}"


def markWinner(results):
    winner_id = 0
    highest_score = 0
    for player in results.values():
        print(player)
        if player.designation == "p":
            if player.score > highest_score:
                highest_score = player.score
                winner_id = player.id
    if winner_id != 0:
        winner_info = results[winner_id]
        results[winner_id] = Scorer(winner_id, winner_info.name, winner_info.score, winner_info.ranking, winner_info.designation, True)


async def getResultsOnPage(results, x, fcm, participants, coaches):
    soup = BeautifulSoup(requests.get(f"https://na.finalfantasyxiv.com/lodestone/ranking/gc/weekly/?page={x}&filter=1"
                                      "&worldname=Siren").content, 'html.parser')
    ranked_peeps = soup.select("tbody tr")
    for result in ranked_peeps:
        player_id = int(str(result["data-href"]).split("/")[3])
        if player_id in fcm:
            score = int(str(result.find("td", {"class": "ranking-character__value"}).text).strip())
            name = str(result.find("h4").contents[0]).strip()
            ranking = int(str(result.select(".ranking-character__number")[0].text).strip())
            designation = "x"
            win = False
            if name in participants and name not in coaches:
                designation = "p"
                participants[name] = "true"
            if name in coaches:
                designation = "c"
                coaches[name] = "true"
            if player_id in results:
                results[player_id] = Scorer(player_id, name, score + results.get(player_id).score, results.get(player_id).ranking, designation, win, True)
            else:
                results[player_id] = Scorer(player_id, name, score, ranking, designation, win)


def get_data(ctx):
    # define database
    conn = sqlite3.connect("data")
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
    conn = sqlite3.connect("data")
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


class Scorer(NamedTuple):
    id: int
    name: str = ""
    score: int = 0
    ranking: int = 0
    designation: str = ""
    winner: bool = False
    duplicate: bool = False

    def __eq__(self, other):
        return self.name == other.name


bot.run(TOKEN)
