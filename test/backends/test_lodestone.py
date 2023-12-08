import unittest
import unittest.mock
import requests

from backends.lodestone import FCMember, LodestoneScraper, LodestoneScraperException


BASE_URL = 'https://some.lodestone.url.com'
FC_ID = 'fc_id'


class FakeResponse:
  def __init__(self, status_code, body):
    self.status_code = status_code
    self.content = body


class TestLodestoneScraper(unittest.TestCase):
  def setUp(self):
    self.scraper = LodestoneScraper(BASE_URL)
    self.mock_responses = {}
    requests.get = self.fake_lodestone_call


  def fake_lodestone_call(self, url):
    return self.mock_responses[url]
  

  def fake_member_entry(self, member):
    return f'''
      <li class="entry"><a href="/lodestone/character/{member.id}/" class="entry__bg">
        <div class="entry__flex">
          <div class="entry__freecompany__center"><p class="entry__name">{member.name}</p>
            <ul class="entry__freecompany__info">
              <li><img src="img-url" width="20"
                      height="20" alt=""><span>{member.rank}</span></li>
            </ul>
          </div>
        </div>
      </a></li>
    '''


  def add_mock_response(self, status, members=None, page=None, max_pages=1):
    if page is None:
      page = 1
      key = f'{BASE_URL}/lodestone/freecompany/{FC_ID}/member'
    else:
      key = f'{BASE_URL}/lodestone/freecompany/{FC_ID}/member?page={page}'

    if members is not None:
      member_entries = '\n'.join(self.fake_member_entry(member) for member in members)
      body = f'''
      <body>
        <ul class="btn__pager">
          <li class="btn__pager__current">Page {page} of {max_pages}</li>
        </ul>
        <ul>
          {member_entries}
        </ul>
      </body>
      '''
    else:
      body = ''

    self.mock_responses[key] = FakeResponse(status, body)


  def test_get_free_company_members_no_members(self):
    self.add_mock_response(status=200, members=[])
    results = self.scraper.get_free_company_members(FC_ID)
    self.assertListEqual(list(results), [])


  def test_get_free_company_members_one_member_one_page(self):
    members=[FCMember('id', 'Kiryuin Satsuki', 'Big Boss')]
    self.add_mock_response(status=200, members=members)
    results = self.scraper.get_free_company_members(FC_ID)
    self.assertListEqual(list(results), members)


  def test_get_free_company_members_two_members_one_page(self):
    members=[FCMember('id', 'Kiryuin Satsuki', 'Big Boss'), FCMember('id2', 'Aia Merry', 'The Boss')]
    self.add_mock_response(status=200, members=members)
    results = self.scraper.get_free_company_members(FC_ID)
    self.assertListEqual(list(results), members)


  def test_get_free_company_members_many_members_three_pages(self):
    page1_members=[FCMember('id', 'Kiryuin Satsuki', 'Big Boss'), FCMember('id2', 'Aia Merry', 'The Boss')]
    page2_members=[FCMember('id3', 'Juhdu Khigbaa', 'Made Member'), FCMember('id4', 'Boy Detective', 'Lieutenant')]
    page3_members = [FCMember('id3', 'Cirina Qalli', 'Officer')]

    self.add_mock_response(status=200, members=page1_members, max_pages=3)
    self.add_mock_response(status=200, members=page2_members, page=2, max_pages=3)
    self.add_mock_response(status=200, members=page3_members, page=3, max_pages=3)

    results = self.scraper.get_free_company_members(FC_ID)
    self.assertListEqual(list(results), page1_members + page2_members + page3_members)

  def test_get_free_company_members_error_states(self):
    self.add_mock_response(404)
    self.assertRaises(LodestoneScraperException, lambda: self.scraper.get_free_company_members(FC_ID))