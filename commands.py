from enum import Enum
from dataclasses import dataclass
import discord
from discord.ext.commands import Context
import string

from backends.lodestone import *


PARTICIPANT_REACTION_EMOJI = '🇵'
COACH_REACTION_EMOJI = '🇨'


class WinnerResult(Enum):
  WINNER = 1
  NO_PARTICIPANTS = 2
  NO_RANKING_PARTICIPANTS = 3


@dataclass
class ProfessionalsScore:
  name: str
  is_ranked: bool = False
  gc_rank: int = -1
  seals: int = -1


@dataclass
class ProfessionalsResults:
  winner_result: WinnerResult
  winner: GrandCompanyRanking
  participant_results: list[GrandCompanyRanking]
  coach_results: list[GrandCompanyRanking]
  honorable_mentions: list[GrandCompanyRanking]


class ChannelSetupException(Exception):
  pass


def to_professionals_score(gc_ranking: GrandCompanyRanking) -> ProfessionalsScore:
    return ProfessionalsScore(gc_ranking.character_name, True, gc_ranking.rank, gc_ranking.seals)


def mention(user_id):
    return f"<@{user_id}>"


async def find_reaction_character_names(ctx: Context, reaction: discord.Reaction) -> set[str]:
  character_names = set()
  async for user in reaction.users():
    discord_name = ctx.guild.get_member(user.id).display_name
    character_names.add(str(discord_name).lstrip(string.punctuation + string.whitespace))
  return character_names


async def find_professionals_signup_message(ctx: Context) -> discord.Message:
    channel = discord.utils.get(ctx.guild.channels, name='professionals-signups')
    if channel is None:
        raise ChannelSetupException('no channel named *professionals-signups* exists')
    professionals_role = discord.utils.get(ctx.guild.roles, name='Professional')
    if professionals_role is None:
        raise ChannelSetupException('no role named *Professional* in channel named *professionals-signups*')
    
    async for message in channel.history(limit=100, oldest_first=False):
      if professionals_role.id in message.raw_role_mentions:
         return message

    raise ChannelSetupException('could not find a message mentioning *Professional* in channel *professionals-signups*')


class CommandHandler:
  def __init__(self, lodestone_scraper: LodestoneScraper):
    self._lodestone_scraper = lodestone_scraper

  
  # def _find_eligible_participants(self, lodestone: LodestoneScraper) -> list[GrandCompanyRanking]:
  #   fc_members = lodestone.get_free_company_members('9231394073691073564')
  #   top_500 = lodestone.get_grand_company_rankings('Siren')
  #   eligible_members = []
  #   for member in fc_members:
  #     gc_ranking = next((rank for rank in top_500 if member.id == rank.id), None)
  #     if gc_ranking is not None:
  #       eligible_members.append(GrandCompanyRanking(member.id, member.name, gc_ranking.rank, gc_ranking.seals))
  #   return eligible_members


  def _collect_results(self, participants: set[str], coaches: set[str]) -> ProfessionalsResults:
    fc_members = self._lodestone_scraper.get_free_company_members('9231394073691073564')
    fc_member_names = list(filter(lambda member: member.name), fc_members)
    top_500 = self._lodestone_scraper.get_grand_company_rankings('Siren')
    fc_members_in_top_500 = filter(lambda rank: rank.character_name in fc_member_names, top_500)

    participant_results = []
    coach_results = []
    honorable_mentions = []
    for fc_member_gc_rank in fc_members_in_top_500:
      if fc_member_gc_rank.character_name in coaches:
        coach_results.append(to_professionals_score(fc_member_gc_rank))
      elif fc_member_gc_rank.character_name in participants:
        participant_results.append(to_professionals_score(fc_member_gc_rank))
      else:
        honorable_mentions.append(to_professionals_score(fc_member_gc_rank))

    participant_results.sort(key=lambda score: score.gc_rank)
    coach_results.sort(key=lambda score: score.gc_rank)
    coach_results.sort(key=lambda score: score.gc_rank)

    if len(participants) == 0:
      winner_result = WinnerResult.NO_PARTICIPANTS
      winner = None
    elif len(participant_results) == 0:
      winner_result = WinnerResult.NO_RANKING_PARTICIPANTS
      winner = None
    else:
      winner_result = WinnerResult.WINNER
      winner = participant_results.pop(0)

    non_ranking_participants = participants - set(p.name for p in participant_results)
    non_ranking_coaches = coaches - set(c.name for c in coach_results)

    participant_results += list(ProfessionalsScore(name) for name in non_ranking_participants)
    coach_results += list(ProfessionalsScore(name) for name in non_ranking_coaches)

    return ProfessionalsResults(winner_result, winner, participant_results, coach_results, honorable_mentions)


  async def handle_professionals_get_results(self, ctx: Context):
    await ctx.message.delete()

    sign_up_message = await find_professionals_signup_message(ctx)

    participants = set()
    coaches = set()
    for reaction in sign_up_message.reactions:
      if reaction.emoji == PARTICIPANT_REACTION_EMOJI:
        participants = await find_reaction_character_names(ctx, reaction)
      elif reaction.emoji == COACH_REACTION_EMOJI:
        coaches = await find_reaction_character_names(ctx, reaction)

    coaches = coaches - participants
    results = self._collect_results(participants, coaches)