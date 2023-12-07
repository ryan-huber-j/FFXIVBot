from bs4 import BeautifulSoup
import re
import requests


_page_number_regex = re.compile('Page \d of (\d)')


class LodestoneScraperException(Exception):
  def __init__(self, status_code, message):
    self.status_code = status_code
    self.__init__(message)


class LodestoneScraperClient:
  def __init__(self, base_url):
    self._base_url = base_url


  def _call_lodestone(self, fc_id, page=None):
    if page is None:
      url = f'{self._base_url}/lodestone/freecompany/{fc_id}/member'
    else:
      url = f'{self._base_url}/lodestone/freecompany/{fc_id}/member?page={page}'

    response = requests.get(url)

    if response.status_code == 404:
      raise LodestoneScraperException(f'Free Company {fc_id} could not be found', response.status_code)
    elif response.status_code >= 400 and response.status_code < 500:
      LodestoneScraperException(f'Failed to access FC {fc_id} members due to an unknown client error', response.status_code)
    elif response.status_code >= 500:
      raise LodestoneScraperException('The Lodestone appears to be down', response.status_code)
    elif response.status_code != 200:
      raise LodestoneScraperException(f'Failed to access FC {fc_id} members due to an unknown issue', response.status_code)
    
    return response
  

  def _scrape_fc_member_names(self, soup):
    fc_member_name_tags = soup.find_all('p', class_='entry__name')
    return [tag.string for tag in fc_member_name_tags]


  def get_free_company_members(self, fc_id):
    response = self._call_lodestone(fc_id)
    soup = BeautifulSoup(response.content, 'html.parser')

    page_number_tag = soup.find('li', class_='btn__pager__current')
    match = _page_number_regex.fullmatch(page_number_tag.string)
    if match is None:
      raise LodestoneScraperException(None, f'Unable to parse page number from following: {page_number_tag.string}')
    num_pages = int(match.group(1))

    member_names = self._scrape_fc_member_names(soup)
    for page_num in range(2, num_pages+1):
      response = self._call_lodestone(fc_id, page_num)
      soup = BeautifulSoup(response.content, 'html.parser')
      member_names += self._scrape_fc_member_names(soup)

    return member_names
