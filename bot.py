import string
import os

import discord
import requests
from discord import app_commands
from bs4 import BeautifulSoup
from typing import NamedTuple

from lodestone import LodestoneScraper
from dotenv import load_dotenv


DUPLICATION_EXPLANATION = " *Note: Defaulted to highest rank listed and combined score between two ranks earned*"
WINNER_MESSAGE = " WINNER"

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(application_id=os.getenv('APPLICATION_ID'), intents=intents)
tree = app_commands.CommandTree(client)
guild = discord.Object(id=int(os.getenv('GUILD_ID')))


def run_bot(discord_token):
    client.run(discord_token)


@client.event
async def on_ready():
    print(f'The bot has connected to Discord!')
    await tree.sync(guild=guild)


@tree.command(
    name="contract",
    description="Submit a contract and earn a payout if you meet your goal!",
    guild=guild
)
@app_commands.describe(
    character_first_name='The first name of your character',
    character_last_name='The last name of your character',
    amount='The number of seals you plan to earn this week'
)
async def create_contract(
    interaction: discord.Interaction,
    character_first_name: str,
    character_last_name: str,
    amount: int,
) -> None:
    await interaction.response.send_message(f"Contract created for {character_first_name} {character_last_name} to earn {amount} seals this week!")


def get_fc_member_ids() -> list[str]:
    scraper = LodestoneScraper('https://na.finalfantasyxiv.com')
    fc_members = scraper.get_free_company_members('9231394073691073564')
    return [member.id for member in fc_members]


@tree.command(
    name="get_results",
    description="Retrieves all FC members' weekly GC ranking results",
    guild=guild
)
async def get_results(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    channel = discord.utils.get(interaction.guild.channels, name='professionals-signups')
    if channel is None:
        await interaction.followup.send("no channel named *professionals-signups* exists")
        return
    role = discord.utils.get(interaction.guild.roles, name="Professional")
    if role is None:
        await interaction.followup.send("no role named *Professional* in channel named *professionals-signups*")
        return
    messages = [message async for message in channel.history(limit=100, oldest_first=False)]
    message = None
    for m in messages:
        if role.id in m.raw_role_mentions:
            message = m
            break
    if message is None:
        await interaction.followup.send("no role named *Professional* mentioned in channel named *professionals-signups*")
        return
    fcm = set(get_fc_member_ids())
    participants = {}
    coaches = {}
    for reaction in message.reactions:
        async for user in reaction.users():
            if reaction.emoji == "🇵":
                participants[str(interaction.guild.get_member(user.id).display_name).lstrip(string.punctuation + string.whitespace)] = "false"
            if reaction.emoji == "🇨":
                coaches[str(interaction.guild.get_member(user.id).display_name).lstrip(string.punctuation + string.whitespace)] = "false"
    results = {}
    msg = None
    for x in range(1, 6):
        await getResultsOnPage(results, x, fcm, participants, coaches)
        if msg:
            await msg.delete()
        msg = await interaction.followup.send(f"{20 * x}% complete")
    if msg:
        await msg.delete()
    
    winner = mark_winner(results)

    if len(results) == 0:
        await interaction.followup.send("Unfortunately I could not find any participants who qualified to win.")
        return

    participant_list = "\n".join(["\n".join(build_score_message(user) for user in results.values() if user.designation == "p"),
                                  "\n".join(f"Rank ???: {user} - **???**" for user in participants if participants[user] == "false" and user not in coaches)])
    coach_list = "\n".join(["\n".join(build_score_message(user) for user in results.values() if user.designation == "c"),
                            "\n".join(f"Rank ???: *{user}* - **???**" for user in coaches if coaches[user] == "false")])
    honorable_mentions_list = "\n".join(build_score_message(user) for user in results.values() if user.designation == "x")

    message_parts = ["✅ Participants\nNote: "
                              "Italicized means that the participant was a coach, not competing for contest prizes."
                              " Ranks Labeled \"???\" were less than the server-wide top 500 or unlisted at all.\n",
                              participant_list.strip(), "\n🛂 Coaches", coach_list.strip(), "\n⚠ Honorable Mentions\n"
                              "These were people who were non-participants but made it to top 500 and were in our FC!",
                              honorable_mentions_list.strip()]


    if winner is not None:
        try:
            winner_discord_id = next(filter(lambda member: member.nick == winner.name, interaction.guild.members)).id
        except (StopIteration):
            await interaction.followup.send(
                f'A winner, "{winner.name}" was found, but I was unable to find their name in Discord to mention them. Please verify that their nickname matches their character name.')
            return
        
        message_parts.append(f"\nFor winning, {mention(winner_discord_id)} gets to choose from:\n"
                               "Any Mog Station Items equaling $10.00 USD (before tax; some Square Enix implemented limitations apply).\n"
                               "or\n"
                               "$10.00 Amazon Gift Card")

    await interaction.followup.send("\n".join(message_parts))


def mention(user_id):
    return f"<@{user_id}>"


def mark_winner(results):
    participants = dict((id, player) for (id, player) in results.items() if player.designation == "p")
    winner_id = max(participants, key=lambda id: participants[id].score, default=None)
    if winner_id is not None:
        winner_info = results[winner_id]
        marked_winner = Scorer(winner_id, winner_info.name, winner_info.score, winner_info.ranking, winner_info.designation, True)
        results[winner_id] = marked_winner
        return marked_winner
    else:
        return None


def build_score_message(player):
    duplication_explanation = DUPLICATION_EXPLANATION if player.duplicate else ""
    win_segment = WINNER_MESSAGE if player.winner else ""
    name_segment = f"*{player.name}*" if player.designation == "c" else player.name

    return f"Rank {player.ranking}: {name_segment} - **{player.score:,}**{win_segment}{duplication_explanation}"


async def getResultsOnPage(results, x, fcm, participants, coaches):
    soup = BeautifulSoup(requests.get(f"https://na.finalfantasyxiv.com/lodestone/ranking/gc/weekly/?page={x}&filter=1"
                                      "&worldname=Siren").content, 'html.parser')
    ranked_peeps = soup.select("tbody tr")
    for result in ranked_peeps:
        player_id = str(result["data-href"]).split("/")[3]
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
