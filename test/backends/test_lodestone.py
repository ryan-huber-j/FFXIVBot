import unittest
import unittest.mock
import requests

from backends.lodestone import LodestoneScraperClient


BASE_URL = 'https://some.lodestone.url.com'
FC_ID = 'fc_id'


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


  def add_mock_response(self, fc_id, response, page=None):
    if page is None:
      key = f'{BASE_URL}/lodestone/freecompany/{fc_id}/member'
    else:
      key = f'{BASE_URL}/lodestone/freecompany/{fc_id}/member?page={page}'
    self.mock_responses[key] = response


  def test_get_free_company_members_no_members(self):
    body = '''
    <body>
      <ul class="btn__pager">
	      <li class="btn__pager__current">Page 1 of 1</li>
      </ul>
      <ul>
		  </ul>
    </body>
    '''

    self.add_mock_response(FC_ID, FakeResponse(200, body))
    results = self.scraper.get_free_company_members(FC_ID)
    self.assertListEqual(list(results), [])


  def test_get_free_company_members_one_member_one_page(self):
    body = '''
    <body>
      <ul class="btn__pager">
	      <li class="btn__pager__current">Page 1 of 1</li>
      </ul>
      <ul>
        <li class="entry">
          <a href="href" class="entry__bg">
            <div class="entry__flex">
              <div class="entry__freecompany__center">
                <p class="entry__name">Kiryuin Satsuki</p>
                </ul>
              </div>
            </div>
          </a>
        </li>
		  </ul>
    </body>
    '''

    self.add_mock_response(FC_ID, FakeResponse(200, body))
    results = self.scraper.get_free_company_members(FC_ID)
    self.assertListEqual(list(results), ['Kiryuin Satsuki'])


  def test_get_free_company_members_two_members_one_page(self):
    body = '''
    <body>
      <ul class="btn__pager">
	      <li class="btn__pager__current">Page 1 of 1</li>
      </ul>
      <ul>
        <li class="entry">
          <a href="href" class="entry__bg">
            <div class="entry__flex">
              <div class="entry__freecompany__center">
                <p class="entry__name">Kiryuin Satsuki</p>
                </ul>
              </div>
            </div>
          </a>
        </li>
        <li class="entry">
          <a href="href" class="entry__bg">
            <div class="entry__flex">
              <div class="entry__freecompany__center">
                <p class="entry__name">Juhdu Khigbaa</p>
                </ul>
              </div>
            </div>
          </a>
        </li>
		  </ul>
    </body>
    '''

    self.add_mock_response(FC_ID, FakeResponse(200, body))
    results = self.scraper.get_free_company_members(FC_ID)
    self.assertListEqual(list(results), ['Kiryuin Satsuki', 'Juhdu Khigbaa'])


  def test_get_free_company_members_many_members_three_pages(self):
    page1 = '''
    <body>
      <ul class="btn__pager">
	      <li class="btn__pager__current">Page 1 of 3</li>
      </ul>
      <ul>
        <li class="entry">
          <a href="href" class="entry__bg">
            <div class="entry__flex">
              <div class="entry__freecompany__center">
                <p class="entry__name">Kiryuin Satsuki</p>
                </ul>
              </div>
            </div>
          </a>
        </li>
        <li class="entry">
          <a href="href" class="entry__bg">
            <div class="entry__flex">
              <div class="entry__freecompany__center">
                <p class="entry__name">Juhdu Khigbaa</p>
                </ul>
              </div>
            </div>
          </a>
        </li>
		  </ul>
    </body>
    '''

    page2 = '''
    <body>
      <ul class="btn__pager">
	      <li class="btn__pager__current">Page 1 of 3</li>
      </ul>
      <ul>
        <li class="entry">
          <a href="href" class="entry__bg">
            <div class="entry__flex">
              <div class="entry__freecompany__center">
                <p class="entry__name">FC Member 3</p>
                </ul>
              </div>
            </div>
          </a>
        </li>
        <li class="entry">
          <a href="href" class="entry__bg">
            <div class="entry__flex">
              <div class="entry__freecompany__center">
                <p class="entry__name">FC Member 4</p>
                </ul>
              </div>
            </div>
          </a>
        </li>
		  </ul>
    </body>
    '''

    page3 = '''
    <body>
      <ul class="btn__pager">
	      <li class="btn__pager__current">Page 1 of 3</li>
      </ul>
      <ul>
        <li class="entry">
          <a href="href" class="entry__bg">
            <div class="entry__flex">
              <div class="entry__freecompany__center">
                <p class="entry__name">FC Member 5</p>
                </ul>
              </div>
            </div>
          </a>
        </li>
		  </ul>
    </body>
    '''

    self.add_mock_response(FC_ID, FakeResponse(200, page1))
    self.add_mock_response(FC_ID, FakeResponse(200, page2), 2)
    self.add_mock_response(FC_ID, FakeResponse(200, page3), 3)

    results = self.scraper.get_free_company_members(FC_ID)
    self.assertListEqual(list(results), ['Kiryuin Satsuki', 'Juhdu Khigbaa', 'FC Member 3', 'FC Member 4', 'FC Member 5'])