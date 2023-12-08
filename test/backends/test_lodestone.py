import unittest
import unittest.mock
import requests

from backends.lodestone import FCMember, GrandCompanyRanking, LodestoneScraper, LodestoneScraperException


BASE_URL = 'https://some.lodestone.url.com'
FC_ID = 'fc_id'
WORLD_NAME = 'Siren'


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


  def add_mock_fc_members_response(self, status, members=None, page=None, max_pages=1):
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
    self.add_mock_fc_members_response(status=200, members=[])
    self.assertListEqual(self.scraper.get_free_company_members(FC_ID), [])


  def test_get_free_company_members_one_member_one_page(self):
    members=[FCMember('id', 'Kiryuin Satsuki', 'Big Boss')]
    self.add_mock_fc_members_response(status=200, members=members)
    self.assertListEqual(self.scraper.get_free_company_members(FC_ID), members)


  def test_get_free_company_members_two_members_one_page(self):
    members=[FCMember('id', 'Kiryuin Satsuki', 'Big Boss'), FCMember('id2', 'Aia Merry', 'The Boss')]
    self.add_mock_fc_members_response(status=200, members=members)
    self.assertListEqual(self.scraper.get_free_company_members(FC_ID), members)


  def test_get_free_company_members_many_members_three_pages(self):
    page1_members=[FCMember('id', 'Kiryuin Satsuki', 'Big Boss'), FCMember('id2', 'Aia Merry', 'The Boss')]
    page2_members=[FCMember('id3', 'Juhdu Khigbaa', 'Made Member'), FCMember('id4', 'Boy Detective', 'Lieutenant')]
    page3_members = [FCMember('id3', 'Cirina Qalli', 'Officer')]

    self.add_mock_fc_members_response(status=200, members=page1_members, max_pages=3)
    self.add_mock_fc_members_response(status=200, members=page2_members, page=2, max_pages=3)
    self.add_mock_fc_members_response(status=200, members=page3_members, page=3, max_pages=3)

    self.assertListEqual(self.scraper.get_free_company_members(FC_ID), page1_members + page2_members + page3_members)


  def test_get_free_company_members_error_states(self):
    for status_code in [400, 404, 429, 500]:
      self.add_mock_fc_members_response(status_code)
      self.assertRaises(LodestoneScraperException, lambda: self.scraper.get_free_company_members(FC_ID))


  def fake_gc_ranking_row(self, ranking: GrandCompanyRanking):
    return f'''
      <tr data-href="/lodestone/character/{ranking.character_id}/" class="clickable">
        <td class="ranking-character__number											"> {ranking.rank} </td>
        <td class="ranking-character__face"> <img
            src="https://img2.finalfantasyxiv.com/f/ba64ef52323ad0c23edaa3bafc9f4e82_58a84e851e55175d22158ca97af58a1ffc0_96x96.jpg?1702063037"
            width="50" height="50" alt=""> </td>
        <td class="ranking-character__info">
          <h4>{ranking.character_name}</h4>
          <p><i class="xiv-lds xiv-lds-home-world js__tooltip" data-tooltip="Home World"></i>Siren [Aether]</p>
        </td>
        <td class="ranking-character__gcrank"> <img
            src="https://lds-img.finalfantasyxiv.com/h/V/tKlwWMAtNLAumnqjI8iNPnMKHc.png" width="32" height="32"
            alt="Immortal Flames/Flame Captain" class="js__tooltip" data-tooltip="Immortal Flames/Flame Captain"> </td>
        <td class="ranking-character__value"> {ranking.seals} </td>
      </tr>
    '''


  def add_mock_gc_rankings_response(self, status_code: int, rankings: list[GrandCompanyRanking] = None, page_num: int = 1):
    if rankings is None:
      body = ''
    else:
      ranking_rows = '\n'.join(self.fake_gc_ranking_row(ranking) for ranking in rankings)
      body = f'''
        <table>
          <tbody>
            {ranking_rows}
          </tbody>
        </table>
      '''

    key = f'{BASE_URL}/lodestone/ranking/gc/weekly?page={page_num}&worldname={WORLD_NAME}'
    self.mock_responses[key] = FakeResponse(status_code, body)


  def test_get_grand_company_rankings_single(self):
    rankings = [GrandCompanyRanking('id', 'Kiryuin Satsuki', 1, 22000000)]
    self.add_mock_gc_rankings_response(200, rankings, 1)
    self.add_mock_gc_rankings_response(200, [], 2)
    self.add_mock_gc_rankings_response(200, [], 3)
    self.add_mock_gc_rankings_response(200, [], 4)
    self.add_mock_gc_rankings_response(200, [], 5)
    self.assertEqual(self.scraper.get_grand_company_rankings(WORLD_NAME), rankings)


  def test_get_grand_company_rankings_two_across_two_pages(self):
    page1_rankings = [GrandCompanyRanking('id', 'Kiryuin Satsuki', 1, 22000000)]
    page2_rankings = [GrandCompanyRanking('id2', 'Vespertine Celeano', 2, 10000000)]
    self.add_mock_gc_rankings_response(200, page1_rankings, 1)
    self.add_mock_gc_rankings_response(200, page2_rankings, 2)
    self.add_mock_gc_rankings_response(200, [], 3)
    self.add_mock_gc_rankings_response(200, [], 4)
    self.add_mock_gc_rankings_response(200, [], 5)
    self.assertEqual(self.scraper.get_grand_company_rankings(WORLD_NAME), page1_rankings + page2_rankings)


  def test_get_grand_company_rankings_many_across_multiple_pages(self):
    page1_rankings = [GrandCompanyRanking('id', 'Kiryuin Satsuki', 1, 22000000), GrandCompanyRanking('id2', 'Vespertine Celeano', 2, 10000000)]
    page2_rankings = [GrandCompanyRanking('id', 'GC Ranking 3', 3, 100000), GrandCompanyRanking('id4', 'GC Ranking 4', 4, 50000)]
    page3_rankings = [GrandCompanyRanking('id', 'GC Ranking 5', 5, 1000)]
    self.add_mock_gc_rankings_response(200, page1_rankings, 1)
    self.add_mock_gc_rankings_response(200, page2_rankings, 2)
    self.add_mock_gc_rankings_response(200, page3_rankings, 3)
    self.add_mock_gc_rankings_response(200, [], 4)
    self.add_mock_gc_rankings_response(200, [], 5)
    self.assertEqual(self.scraper.get_grand_company_rankings(WORLD_NAME), page1_rankings + page2_rankings + page3_rankings)


  def test_get_grand_company_rankings_error_states(self):
    for status_code in [400, 404, 429, 500]:
      self.add_mock_gc_rankings_response(status_code)
      self.assertRaises(LodestoneScraperException, lambda: self.scraper.get_grand_company_rankings(WORLD_NAME))