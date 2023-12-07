import unittest
import unittest.mock
import requests

from backends.lodestone import LodestoneScraperClient


BASE_URL = 'https://some.lodestone.url.com'


class FakeResponse:
  def __init__(self, status_code, body):
    self.status_code = status_code
    self.content = body


class TestLodestoneScraper(unittest.TestCase):
  def setUp(self):
    self.scraper = LodestoneScraperClient(BASE_URL)
    self.mock_responses = {}
    requests.get = self.fake_lodestone_call

  def fake_lodestone_call(self, url):
    return self.mock_responses[url]
  
  def add_mock_response(self, fc_id, response):
    self.mock_responses[f'{BASE_URL}/lodestone/freecompany/{fc_id}/member'] = response

  def test_get_free_company_members_no_members(self):
    fc_id = 'empty_response'
    body = '''
    <body>
      <ul class="btn__pager">
	      <li class="btn__pager__current">Page 1 of 3</li>
      </ul>
      <ul>
		  </ul>
    </body>
    '''

    self.add_mock_response(fc_id, FakeResponse(200, '<body></body>'))
    results = self.scraper.get_free_company_members(fc_id)
    self.assertListEqual(list(results), [])