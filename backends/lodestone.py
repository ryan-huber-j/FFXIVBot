from bs4 import BeautifulSoup
import requests


class LodestoneScraperException(Exception):
  def __init__(self, status_code, message):
    self.status_code = status_code
    self.__init__(message)


class LodestoneScraperClient:
  _base_url = None

  def __init__(self, base_url):
    self._base_url = base_url

  def get_free_company_members(self, fc_id):
    # https://na.finalfantasyxiv.com/lodestone/freecompany/9231394073691073564/member/
    response = requests.get(f'{self._base_url}/lodestone/freecompany/{fc_id}/member')

    if response.status_code == 404:
      raise LodestoneScraperException(f'Free Company {fc_id} could not be found', response.status_code)
    elif response.status_code >= 400 and response.status_code < 500:
      LodestoneScraperException(f'Failed to access FC {fc_id} members due to an unknown client error', response.status_code)
    elif response.status_code >= 500:
      raise LodestoneScraperException('The Lodestone appears to be down', response.status_code)
    elif response.status_code != 200:
      raise LodestoneScraperException(f'Failed to access FC {fc_id} members due to an unknown issue', response.status_code)
    
    soup = BeautifulSoup(response.content, 'html.parser')
    fc_member_name_tags = soup.find_all('p', class_='entry__name')

    return [tag.string for tag in fc_member_name_tags]
