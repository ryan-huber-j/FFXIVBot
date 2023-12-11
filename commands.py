from dataclasses import dataclass
import discord
from discord.ext.commands import Context
import string

from backends.lodestone import *


def mention(user_id):
    return f"<@{user_id}>"


def find_user_character_name(ctx: Context, user: discord.User):
  display_name = ctx.guild.get_member(user.id).display_name
  return str(display_name).lstrip(string.punctuation + string.whitespace)


async def find_professionals_signup_message(ctx) -> discord.Message:
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


@dataclass
class ProfessionalsParticipant:
  character_id: str
  character_name: str
  gc_rank_number: int
  seals: int


class ChannelSetupException(Exception):
  pass


class CommandHandler:
  def __init__(self, lodestone_scraper: LodestoneScraper):
    self._lodestone_scraper = lodestone_scraper

  
  def _find_eligible_participants(self, lodestone: LodestoneScraper) -> list[ProfessionalsParticipant]:
    fc_members = lodestone.get_free_company_members('9231394073691073564')
    top_500 = lodestone.get_grand_company_rankings('Siren')
    eligible_members = []
    for member in fc_members:
      gc_ranking = next((rank for rank in top_500 if member.id == rank.id), None)
      if gc_ranking is not None:
        eligible_members.append(ProfessionalsParticipant(member.id, member.name, gc_ranking.rank, gc_ranking.seals))
    return eligible_members


  async def handle_professionals_get_results(self, ctx: Context):
    await ctx.message.delete()

    sign_up_message = await find_professionals_signup_message(ctx)
    eligible_participants = self._find_eligible_participants(self._lodestone_scraper)

    participants = set()
    coaches = set()
    for reaction in sign_up_message.reactions:
      if reaction.emoji == '🇵':
        participants = set(async member.)


    pass
