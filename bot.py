import os
import string
import textwrap
from typing import Iterable, NamedTuple

from bs4 import BeautifulSoup
import discord
from discord import app_commands
from dotenv import load_dotenv
import requests

from db import SqlLiteClient
from domain import (
    CompetitionResults,
    Contract,
    ContractInput,
    HonorableMention,
    Participant,
    PlayerScore,
    UserException,
    ValidationException,
    WinReason,
)
from lodestone import LodestoneScraper
import professionals

DUPLICATION_EXPLANATION = " *Note: Defaulted to highest rank listed and combined score between two ranks earned*"
WINNER_MESSAGE = " WINNER"

PARTICIPANT_MESSAGE_TEMPLATE = """
## ✅ Participants
Note: ranks Labeled "???" were less than the server-wide top 500 or unlisted at all.
{}
""".strip()
COACHES_MESSAGE_TEMPLATE = "## 🛂 Coaches\n{}"

HONORABLE_MENTIONS_MESSAGE_TEMPLATE = """
## ⚠ **Honorable Mentions**
These were people who were non-participants but made it to top 500 and were in our FC!
{}
""".strip()

WINNER_MESSAGE_TEMPLATE = """
## Competition Winner
The winner for this week is: {mention_winner}!

For winning, {mention_winner} gets to choose from:
Any Mog Station Items equaling $10.00 USD (before tax; some Square Enix implemented limitations apply).
or
$10.00 Amazon Gift Card
""".strip()

CONTRACTS_MESSAGE_TEMPLATE = """
## 📜 Contracts this Week
{}
""".strip()

CREDITS_MESSAGE_TEMPLATE = "Special thanks to {} for maintaining our Discord bot {} to help with rank info collection!"

DRAWING_MESSAGE_TEMPLATE = (
    "## Random Drawing\n"
    "Winner of the Random Prize - Gil Drawing was awarded to {}! An extra 350,000 Gil was "
    "sent to them! Remember: This prize is awarded to folks who didn't win the Mog "
    "Station prizes this week but still scored in the top 500 as a participant! Please "
    "make sure to sign up if you plan to participate to ensure you can be counted. See "
    "the Honorable Mentions list to see if YOU made the top 500 this week."
)

contract_payouts = {
    300000: 450000,
    420000: 550000,
    500000: 650000,
    800000: 900000,
    1000000: 3200000,
}


load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(application_id=os.getenv("APPLICATION_ID"), intents=intents)
tree = app_commands.CommandTree(client)
guild: discord.Guild = discord.Object(id=int(os.getenv("GUILD_ID")))
professionals_channel = None


def run_bot(discord_token: str):
    professionals.initialize(
        SqlLiteClient(), LodestoneScraper("https://na.finalfantasyxiv.com")
    )
    client.run(discord_token)


@client.event
async def on_ready():
    await tree.sync(guild=guild)
    global professionals_channel
    professionals_channel = discord.utils.get(
        client.get_all_channels(), name="professionals-signups"
    )
    print(f"The bot has connected to Discord!")


def mention(user_id: int) -> str:
    return f"<@{user_id}>"


def italicize(text: str) -> str:
    return f"*{text}*"


def get_signups_channel():
    return discord.utils.get(client.get_all_channels(), name="professionals-signups")


def get_professionals_role():
    return discord.utils.get(guild.roles, name="Professional")


def follow_up_to_user(interaction: discord.Interaction, message: str):
    return interaction.followup.send(message, ephemeral=True)


def present_validation_errors(ve: professionals.ValidationException) -> str:
    lines = "\n".join([f"**{field}:** {message}" for field, message in ve.errors])
    return textwrap.dedent(f"One or more fields were invalid:\n{lines}")


async def invoke_with_exception_handling(
    interaction: discord.Interaction, func, *args, **kwargs
):
    try:
        result = await func(*args, **kwargs)
        return result
    except ValidationException as ve:
        await follow_up_to_user(interaction, present_validation_errors(ve))
        raise ve
    except UserException as pe:
        await follow_up_to_user(interaction, pe.user_message)
        raise pe
    except Exception as e:
        await follow_up_to_user(interaction, "An unexpected error occurred")
        raise e


@tree.command(
    name="participate",
    description="Become a professional and earn rewards!",
    guild=guild,
)
@app_commands.describe(
    character_first_name="The first name of your character",
    character_last_name="The last name of your character",
)
@app_commands.checks.has_role("Professional")
async def participate(
    interaction: discord.Interaction,
    character_first_name: str,
    character_last_name: str,
):
    await interaction.response.defer(ephemeral=True, thinking=True)

    await invoke_with_exception_handling(
        interaction,
        professionals.participate_as_player,
        interaction.user.id,
        character_first_name,
        character_last_name,
    )

    msg = f"Registered {character_first_name} {character_last_name} as a participant."
    await follow_up_to_user(interaction, msg)


@tree.command(
    name="coach",
    description="Become a professional, but do not earn rewards.",
    guild=guild,
)
@app_commands.describe(
    character_first_name="The first name of your character",
    character_last_name="The last name of your character",
)
@app_commands.checks.has_role("Professional")
async def coach(
    interaction: discord.Interaction,
    character_first_name: str,
    character_last_name: str,
):
    await interaction.response.defer(ephemeral=True, thinking=True)

    await invoke_with_exception_handling(
        interaction,
        professionals.participate_as_coach,
        interaction.user.id,
        character_first_name,
        character_last_name,
    )

    msg = f"Registered {character_first_name} {character_last_name} as a coach."
    await follow_up_to_user(interaction, msg)


@tree.command(
    name="end_participation",
    description="End your participation as a professional.",
    guild=guild,
)
@app_commands.checks.has_role("Professional")
async def end_participation(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)

    await invoke_with_exception_handling(
        interaction, professionals.end_participation, interaction.user.id
    )

    msg = f"Withdrew {interaction.user.display_name} from professionals."
    await follow_up_to_user(interaction, msg)


@tree.command(
    name="contract",
    description="Submit a contract and earn a payout if you meet your goal!",
    guild=guild,
)
@app_commands.describe(
    character_first_name="The first name of your character",
    character_last_name="The last name of your character",
    amount="The number of seals you plan to earn this week",
)
@app_commands.checks.has_role("Professional")
async def create_contract(
    interaction: discord.Interaction,
    amount: int,
    character_first_name: str = "",
    character_last_name: str = "",
) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)

    contract_input = ContractInput(
        discord_id=interaction.user.id,
        first_name=character_first_name,
        last_name=character_last_name,
        amount=amount,
        contract_amounts=[300000, 420000, 500000, 800000, 1000000],
    )

    await invoke_with_exception_handling(
        interaction, professionals.create_contract, contract_input
    )

    msg = (
        f"Contract created for {character_first_name} {character_last_name} to "
        f"earn {amount} seals per week."
        if character_first_name and character_last_name
        else f"Contract created to earn {amount} seals per week."
    )
    await follow_up_to_user(interaction, msg)


@tree.command(
    name="end_contract",
    description="End your current contract.",
    guild=guild,
)
@app_commands.checks.has_role("Professional")
async def end_contract(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)

    await invoke_with_exception_handling(
        interaction, professionals.end_contract, interaction.user.id
    )

    msg = f"Ended contract for {interaction.user.display_name}."
    await follow_up_to_user(interaction, msg)


async def consume_results(interaction: discord.Interaction) -> CompetitionResults:
    async for result in professionals.get_competition_results(contract_payouts):
        if isinstance(result, str):
            await follow_up_to_user(interaction, result)
        elif isinstance(result, CompetitionResults):
            return result
        else:
            raise Exception("Received unknown result type from get_competition_results")


def format_participant_list(players: list[PlayerScore | HonorableMention]) -> str:
    lines = []
    for p in players:
        line = f"Rank {p.rank}: {p.first_name} {p.last_name} - **{p.seals_earned:,}**"
        lines.append(line)
    return "\n".join(lines)


def format_participants_msg(players: list[Participant]) -> str:
    if len(players) == 0:
        participant_msg = italicize("No participants this week.")
    else:
        participant_msg = format_participant_list(players)
    return PARTICIPANT_MESSAGE_TEMPLATE.format(participant_msg)


def format_coach_msg(coaches: list[Participant]) -> str:
    if len(coaches) == 0:
        coach_msg = italicize("No coaches this week.")
    else:
        coach_msg = format_participant_list(coaches)
    return COACHES_MESSAGE_TEMPLATE.format(coach_msg)


def format_honorable_mentions_msg(mentions: list[HonorableMention]) -> str:
    if len(mentions) == 0:
        return italicize("No honorable mentions this week.")
    return HONORABLE_MENTIONS_MESSAGE_TEMPLATE.format(format_participant_list(mentions))


def format_contracts(contracts: list[Contract]) -> str:
    if len(contracts) == 0:
        return italicize("No contracts this week.")

    lines = []
    for cr in contracts:
        if cr.is_completed:
            contract_line = (
                f"{cr.first_name} {cr.last_name}: {cr.amount:,} seals"
                f" -- Payout: {cr.payout:,} gil"
            )
        else:
            contract_line = (
                "~~"
                f"~~{cr.first_name} {cr.last_name}: {cr.amount:,} seals"
                " -- Contract Incomplete"
                "~~"
            )
        lines.append(contract_line)
    return CONTRACTS_MESSAGE_TEMPLATE.format("\n".join(lines))


def format_results_message(
    interaction: discord.Interaction, results: CompetitionResults
) -> str:
    participant_scores = [p for p in results.player_scores if not p.is_coach]
    participant_msg = format_participants_msg(participant_scores)
    coach_scores = [p for p in results.player_scores if p.is_coach]
    coaches_msg = format_coach_msg(coach_scores)
    honorable_mentions_msg = format_honorable_mentions_msg(results.honorable_mentions)

    if results.competition_win_reason == WinReason.NO_ELIGIBLE_PLAYERS:
        winner_msg = None
    else:
        winner_msg = WINNER_MESSAGE_TEMPLATE.format(
            mention_winner=mention(results.competition_winner.discord_id),
        )

    contracts_msg = format_contracts(results.contract_results)
    credits_msg = CREDITS_MESSAGE_TEMPLATE.format(
        mention(interaction.user.id), mention(client.user.id)
    )

    if results.drawing_win_reason == WinReason.NO_ELIGIBLE_PLAYERS:
        drawing_msg = None
    else:
        drawing_msg = DRAWING_MESSAGE_TEMPLATE.format(
            results.drawing_winner.first_name + " " + results.drawing_winner.last_name,
        )

    msg_parts = [
        "# Competition Results",
        participant_msg,
        coaches_msg,
        honorable_mentions_msg,
        winner_msg,
        contracts_msg,
        credits_msg,
        drawing_msg,
    ]
    msg = "\n".join(part for part in msg_parts if part is not None)
    return msg


@tree.command(
    name="post_competition_results",
    description="Retrieves all FC members' weekly GC ranking results",
    guild=guild,
)
@app_commands.checks.has_role("Professional")
async def post_competition_results(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)

    results: CompetitionResults = await invoke_with_exception_handling(
        interaction, consume_results, interaction
    )

    msg = format_results_message(interaction, results)
    await professionals_channel.send(msg)
