from bs4 import BeautifulSoup
from dataclasses import dataclass
import re
import requests


_page_number_regex = re.compile('Page \d of (\d)')
_character_link_regex = re.compile('/lodestone/character/(.+)/')


@dataclass
class FCMember:
  id: str
  name: str
  rank: str


@dataclass
class GrandCompanyRanking:
  id: str
  name: str
  rank: int
  company_seals: int


class LodestoneScraperException(Exception):
  def __init__(self, message: str, status_code: int = None):
    super().__init__(message)
    self.status_code = status_code


class LodestoneScraper:
  def __init__(self, base_url: str):
    self._base_url = base_url


  def _get_fc_members_page(self, fc_id: str, page_num: int = None):
    if page_num is None:
      url = f'{self._base_url}/lodestone/freecompany/{fc_id}/member'
    else:
      url = f'{self._base_url}/lodestone/freecompany/{fc_id}/member?page={page_num}'

    response = requests.get(url)

    if response.status_code == 404:
      raise LodestoneScraperException(f'Free Company {fc_id} could not be found', response.status_code)
    elif response.status_code == 429:
      raise LodestoneScraperException(f'Unable to fetch Free Company members due to Lodestone rate limiting')
    elif response.status_code >= 400 and response.status_code < 500:
      raise LodestoneScraperException(f'Failed to access FC {fc_id} members due to an unknown client error', response.status_code)
    elif response.status_code >= 500:
      raise LodestoneScraperException('The Lodestone appears to be down', response.status_code)
    elif response.status_code != 200:
      raise LodestoneScraperException(f'Failed to access FC {fc_id} members due to an unknown issue', response.status_code)
    
    return response
  

  def _scrape_members_from_page(self, page: BeautifulSoup):
    fc_members = []

    member_list_items_tags = page.find_all('li', class_='entry')
    for member_tag in member_list_items_tags:
      character_link_tag = member_tag.find('a', class_='entry__bg')
      character_link = character_link_tag['href']
      lodestone_id_match = _character_link_regex.fullmatch(character_link)
      if lodestone_id_match is None:
        raise LodestoneScraperException(f'Unable to parse character lodestone ID from following: {character_link}')
      lodestone_id = lodestone_id_match.group(1)

      member_name = member_tag.find('p', class_='entry__name').string

      member_fc_info_tag = member_tag.find('ul', class_='entry__freecompany__info')
      member_rank = member_fc_info_tag.find('li').find('span').string

      fc_members.append(FCMember(lodestone_id, member_name, member_rank))

    return fc_members
  

  def _fetch_grand_company_rankings_page(self, world: str, page_num: int = 1):
    response = requests.get(
      f"https://na.finalfantasyxiv.com/lodestone/ranking/gc/weekly?"
      "page={page_num}&filter=1&worldname={world}"
    )

    if response.status_code == 404:
      raise LodestoneScraperException(f'Could not find Grand Company rankings for {world}', response.status_code)
    elif response.status_code == 429:
      raise LodestoneScraperException(f'Unable to fetch Grand Company rankings due to Lodestone rate limiting')
    elif response.status_code >= 400 and response.status_code < 500:
      LodestoneScraperException(f'Could not find Grand Company rankings due to an unknown client error', response.status_code)
    elif response.status_code >= 500:
      raise LodestoneScraperException('The Lodestone appears to be down', response.status_code)
    elif response.status_code != 200:
      raise LodestoneScraperException(f'Could not find Grand Company rankings due to an unknown issue', response.status_code)


  def get_free_company_members(self, fc_id: str):
    response = self._get_fc_members_page(fc_id)
    soup = BeautifulSoup(response.content, 'html.parser')

    page_number_tag = soup.find('li', class_='btn__pager__current')
    match = _page_number_regex.fullmatch(page_number_tag.string)
    if match is None:
      raise LodestoneScraperException(f'Unable to parse page number from following: {page_number_tag.string}')
    num_pages = int(match.group(1))

    members = self._scrape_members_from_page(soup)
    for page_num in range(2, num_pages+1):
      response = self._get_fc_members_page(fc_id, page_num)
      soup = BeautifulSoup(response.content, 'html.parser')
      members += self._scrape_members_from_page(soup)

    return members
  
  def get_grand_company_rankings(self, world: str):
    pass