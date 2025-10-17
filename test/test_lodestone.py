import unittest

import responses

from lodestone import *

BASE_URL = 'https://some.lodestone.url.com'
FC_ID = 'fc_id'
WORLD_NAME = 'Siren'



def fake_member_entry(member):
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


def mock_fc_members_response(status, members=None, page=None, max_pages=1):
  if page is None:
    page = 1
    url = f'{BASE_URL}/lodestone/freecompany/{FC_ID}/member'
  else:
    url = f'{BASE_URL}/lodestone/freecompany/{FC_ID}/member?page={page}'

  matchers = [responses.matchers.query_param_matcher({'page': str(page)})] if page > 1 else []

  if members is not None:
    member_entries = '\n'.join(fake_member_entry(member) for member in members)
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

  return responses.Response(
      responses.GET,
      url,
      body=body,
      status=status,
      match=matchers
  )


def fake_gc_ranking_row(ranking: GrandCompanyRanking):
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


def mock_gc_rankings_response(status_code: int, rankings: list[GrandCompanyRanking] = None, page_num: int = 1):
  if rankings is None:
    body = ''
  else:
    ranking_rows = '\n'.join(fake_gc_ranking_row(ranking) for ranking in rankings)
    body = f'''
      <table>
        <tbody>
          {ranking_rows}
        </tbody>
      </table>
    '''

  url = f'{BASE_URL}/lodestone/ranking/gc/weekly?page={page_num}&worldname={WORLD_NAME}'
  return responses.Response(
      responses.GET,
      url,
      body=body,
      status=status_code,
      content_type='text/html'
  )


def mock_free_companies_response(status_code: int, fcs: list[FreeCompany] = []):
  key = f'{BASE_URL}/lodestone/freecompany?worldname={WORLD_NAME}'

  fc_html_elems = []
  for free_company in fcs:
    html = f'''
      <div class="entry">
        <a href="/lodestone/freecompany/{free_company.id}/" class="entry__block">
          <div class="entry__freecompany__inner">
            <div class="entry__freecompany__box">
              <p class="entry__world">Maelstrom</p>
              <p class="entry__name">{free_company.name}</p>
              <p class="entry__world"><i class="xiv-lds xiv-lds-home-world js__tooltip" data-tooltip="Home World"></i>{WORLD_NAME}
                [Aether]</p>
            </div>
          </div>
          <ul class="entry__freecompany__fc-data clearix">
            <li class="entry__freecompany__fc-member">35</li>
            <li class="entry__freecompany__fc-housing">Estate Built</li>
            <li class="entry__freecompany__fc-day"><span id="datetime-f106dabe182">09/20/2021</span>
              <script>document.getElementById('datetime-f106dabe182').innerHTML = ldst_strftime(1632175472, 'YMD');</script>
            </li>
            <li class="entry__freecompany__fc-active">Active: Always</li>
            <li class="entry__freecompany__fc-active">Recruitment: Open</li>
          </ul>
        </a>
      </div>
    '''
    fc_html_elems.append(html)
  
  body = f'''
    <div>
      {''.join(fc_html_elems)}
    </div>
  '''

  return responses.Response(
      responses.GET,
      key,
      body=body,
      status=status_code,
      content_type='text/html'
  )


class TestLodestoneScraper(unittest.TestCase):
  def setUp(self):
    self.scraper = LodestoneScraper(BASE_URL)


  @responses.activate
  def test_get_free_company_members_no_members(self):
    response = mock_fc_members_response(status=200, members=[])
    responses.add(response)
    self.assertListEqual(self.scraper.get_free_company_members(FC_ID), [])


  @responses.activate
  def test_get_free_company_members_one_member_one_page(self):
    members=[FCMember('id', 'Kiryuin Satsuki', 'Big Boss')]
    response = mock_fc_members_response(status=200, members=members)
    responses.add(response)
    self.assertListEqual(self.scraper.get_free_company_members(FC_ID), members)


  @responses.activate
  def test_get_free_company_members_two_members_one_page(self):
    members=[FCMember('id', 'Kiryuin Satsuki', 'Big Boss'), FCMember('id2', 'Aia Merry', 'The Boss')]
    response = mock_fc_members_response(status=200, members=members)
    responses.add(response)
    self.assertListEqual(self.scraper.get_free_company_members(FC_ID), members)


  @responses.activate
  def test_get_free_company_members_many_members_three_pages(self):
    page1_members = [FCMember('id', 'Kiryuin Satsuki', 'Big Boss'), FCMember('id2', 'Aia Merry', 'The Boss')]
    page2_members = [FCMember('id3', 'Juhdu Khigbaa', 'Made Member'), FCMember('id4', 'Boy Detective', 'Lieutenant')]
    page3_members = [FCMember('id3', 'Cirina Qalli', 'Officer')]

    page1_response = mock_fc_members_response(status=200, members=page1_members, max_pages=3)
    page2_response = mock_fc_members_response(status=200, members=page2_members, page=2, max_pages=3)
    page3_response = mock_fc_members_response(status=200, members=page3_members, page=3, max_pages=3)

    responses.add(page1_response)
    responses.add(page2_response)
    responses.add(page3_response)

    self.assertListEqual(self.scraper.get_free_company_members(FC_ID), page1_members + page2_members + page3_members)


  @responses.activate
  def test_get_free_company_members_error_states(self):
    for status_code in [400, 404, 429, 500]:
      response = mock_fc_members_response(status_code)
      responses.add(response)
      self.assertRaises(LodestoneScraperException, lambda: self.scraper.get_free_company_members(FC_ID))


  @responses.activate
  def test_get_grand_company_rankings_single(self):
    rankings = [GrandCompanyRanking('id', 'Kiryuin Satsuki', 1, 22000000)]
    responses.add(mock_gc_rankings_response(200, rankings, 1))
    responses.add(mock_gc_rankings_response(200, [], 2))
    responses.add(mock_gc_rankings_response(200, [], 3))
    responses.add(mock_gc_rankings_response(200, [], 4))
    responses.add(mock_gc_rankings_response(200, [], 5))
    self.assertEqual(self.scraper.get_grand_company_rankings(WORLD_NAME), rankings)


  @responses.activate
  def test_get_grand_company_rankings_two_across_two_pages(self):
    page1_rankings = [GrandCompanyRanking('id', 'Kiryuin Satsuki', 1, 22000000)]
    page2_rankings = [GrandCompanyRanking('id2', 'Vespertine Celeano', 2, 10000000)]
    responses.add(mock_gc_rankings_response(200, page1_rankings, 1))
    responses.add(mock_gc_rankings_response(200, page2_rankings, 2))
    responses.add(mock_gc_rankings_response(200, [], 3))
    responses.add(mock_gc_rankings_response(200, [], 4))
    responses.add(mock_gc_rankings_response(200, [], 5))
    self.assertEqual(self.scraper.get_grand_company_rankings(WORLD_NAME), page1_rankings + page2_rankings)


  @responses.activate
  def test_get_grand_company_rankings_many_across_multiple_pages(self):
    page1_rankings = [GrandCompanyRanking('id', 'Kiryuin Satsuki', 1, 22000000), GrandCompanyRanking('id2', 'Vespertine Celeano', 2, 10000000)]
    page2_rankings = [GrandCompanyRanking('id', 'GC Ranking 3', 3, 100000), GrandCompanyRanking('id4', 'GC Ranking 4', 4, 50000)]
    page3_rankings = [GrandCompanyRanking('id', 'GC Ranking 5', 5, 1000)]
    responses.add(mock_gc_rankings_response(200, page1_rankings, 1))
    responses.add(mock_gc_rankings_response(200, page2_rankings, 2))
    responses.add(mock_gc_rankings_response(200, page3_rankings, 3))
    responses.add(mock_gc_rankings_response(200, [], 4))
    responses.add(mock_gc_rankings_response(200, [], 5))
    self.assertEqual(self.scraper.get_grand_company_rankings(WORLD_NAME), page1_rankings + page2_rankings + page3_rankings)


  @responses.activate
  def test_get_grand_company_rankings_error_states(self):
    for status_code in [400, 404, 429, 500]:
      responses.add(mock_gc_rankings_response(status_code))
      self.assertRaises(LodestoneScraperException, lambda: self.scraper.get_grand_company_rankings(WORLD_NAME))


  @responses.activate
  def test_search_free_companies_empty(self):
    response = mock_free_companies_response(200)
    responses.add(response)
    self.assertEqual(self.scraper.search_free_companies(WORLD_NAME), [])

  
  @responses.activate
  def test_search_free_companies_single(self):
    single_fc = [FreeCompany('1234', 'Free Company 1')]
    response = mock_free_companies_response(200, single_fc)
    responses.add(response)
    self.assertEqual(self.scraper.search_free_companies(WORLD_NAME), single_fc)


  @responses.activate
  def test_get_grand_company_rankings_error_states(self):
    for status_code in [400, 404, 429, 500]:
      response = mock_free_companies_response(status_code)
      responses.add(response)
      self.assertRaises(LodestoneScraperException, lambda: self.scraper.search_free_companies(WORLD_NAME))