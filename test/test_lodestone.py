from test.request_mocking import *
import unittest

import responses

from lodestone import *

HOSTNAME = "some.lodestone.url.com"
FC_ID = "fc_id"
WORLD_NAME = "Siren"


class TestGetFreeCompanyMembers(unittest.TestCase):
    def setUp(self):
        self.scraper = LodestoneScraper("https://" + HOSTNAME)

    @responses.activate
    def test_no_members(self):
        response = mock_fc_members_response(HOSTNAME, 200, FC_ID, members=[])
        responses.add(response)
        self.assertListEqual(self.scraper.get_free_company_members(FC_ID), [])

    @responses.activate
    def test_one_member_one_page(self):
        members = [FCMember("id", "Kiryuin Satsuki", "Big Boss")]
        response = mock_fc_members_response(HOSTNAME, 200, FC_ID, members=members)
        responses.add(response)
        self.assertListEqual(self.scraper.get_free_company_members(FC_ID), members)

    @responses.activate
    def test_two_members_on_one_page(self):
        members = [
            FCMember("id", "Kiryuin Satsuki", "Big Boss"),
            FCMember("id2", "Aia Merry", "The Boss"),
        ]
        response = mock_fc_members_response(HOSTNAME, 200, FC_ID, members=members)
        responses.add(response)
        self.assertListEqual(self.scraper.get_free_company_members(FC_ID), members)

    @responses.activate
    def test_many_members_over_three_pages(self):
        page1_members = [
            FCMember("id", "Kiryuin Satsuki", "Big Boss"),
            FCMember("id2", "Aia Merry", "The Boss"),
        ]
        page2_members = [
            FCMember("id3", "Juhdu Khigbaa", "Made Member"),
            FCMember("id4", "Boy Detective", "Lieutenant"),
        ]
        page3_members = [FCMember("id3", "Cirina Qalli", "Officer")]

        page1_response = mock_fc_members_response(
            HOSTNAME, 200, FC_ID, members=page1_members, max_pages=3
        )
        page2_response = mock_fc_members_response(
            HOSTNAME, 200, FC_ID, members=page2_members, page=2, max_pages=3
        )
        page3_response = mock_fc_members_response(
            HOSTNAME, 200, FC_ID, members=page3_members, page=3, max_pages=3
        )

        responses.add(page1_response)
        responses.add(page2_response)
        responses.add(page3_response)

        self.assertListEqual(
            self.scraper.get_free_company_members(FC_ID),
            page1_members + page2_members + page3_members,
        )

    @responses.activate
    def test_error_states(self):
        for status_code in [400, 404, 429, 500]:
            response = mock_fc_members_response(HOSTNAME, status_code, FC_ID)
            responses.add(response)
            self.assertRaises(
                LodestoneScraperException,
                lambda: self.scraper.get_free_company_members(FC_ID),
            )


class TestGetGrandCompanyRankings(unittest.TestCase):
    def setUp(self):
        self.scraper = LodestoneScraper("https://" + HOSTNAME)

    @responses.activate
    def test_single_grand_company(self):
        rankings = [GrandCompanyRanking("id", "Kiryuin Satsuki", 1, 22000000)]
        register_gc_pages(HOSTNAME, WORLD_NAME, rankings)
        self.assertEqual(self.scraper.get_grand_company_rankings(WORLD_NAME), rankings)

    @responses.activate
    def test_two_pages(self):
        page1_rankings = [GrandCompanyRanking("id", "Kiryuin Satsuki", 1, 22000000)]
        page2_rankings = [GrandCompanyRanking("id2", "Vespertine Celeano", 2, 10000000)]
        register_gc_page(HOSTNAME, WORLD_NAME, page1_rankings, page_num=1)
        register_gc_page(HOSTNAME, WORLD_NAME, page2_rankings, page_num=2)
        register_empty_gc_pages(HOSTNAME, WORLD_NAME, start_page=3, pages=5)
        self.assertEqual(
            self.scraper.get_grand_company_rankings(WORLD_NAME),
            page1_rankings + page2_rankings,
        )

    @responses.activate
    def test_multiple_rankings_across_multiple_pages(self):
        page1_rankings = [
            GrandCompanyRanking("id", "Kiryuin Satsuki", 1, 22000000),
            GrandCompanyRanking("id2", "Vespertine Celeano", 2, 10000000),
        ]
        page2_rankings = [
            GrandCompanyRanking("id", "GC Ranking 3", 3, 100000),
            GrandCompanyRanking("id4", "GC Ranking 4", 4, 50000),
        ]
        page3_rankings = [GrandCompanyRanking("id", "GC Ranking 5", 5, 1000)]
        register_gc_page(HOSTNAME, WORLD_NAME, page1_rankings, page_num=1)
        register_gc_page(HOSTNAME, WORLD_NAME, page2_rankings, page_num=2)
        register_gc_page(HOSTNAME, WORLD_NAME, page3_rankings, page_num=3)
        register_empty_gc_pages(HOSTNAME, WORLD_NAME, start_page=4, pages=5)
        self.assertEqual(
            self.scraper.get_grand_company_rankings(WORLD_NAME),
            page1_rankings + page2_rankings + page3_rankings,
        )

    @responses.activate
    def test_error_states(self):
        for status_code in [400, 404, 429, 500]:
            responses.add(
                mock_gc_rankings_response(HOSTNAME, status_code, WORLD_NAME, None, 1)
            )
            self.assertRaises(
                LodestoneScraperException,
                lambda: self.scraper.get_grand_company_rankings(WORLD_NAME),
            )


class TestSearchFreeCompanies(unittest.TestCase):
    def setUp(self):
        self.scraper = LodestoneScraper("https://" + HOSTNAME)

    @responses.activate
    def test_empty(self):
        response = mock_free_companies_response(HOSTNAME, 200, WORLD_NAME)
        responses.add(response)
        self.assertEqual(self.scraper.search_free_companies(WORLD_NAME), [])

    @responses.activate
    def test_single(self):
        single_fc = [FreeCompany("1234", "Free Company 1")]
        response = mock_free_companies_response(HOSTNAME, 200, WORLD_NAME, single_fc)
        responses.add(response)
        self.assertEqual(self.scraper.search_free_companies(WORLD_NAME), single_fc)

    @responses.activate
    def test_error_states(self):
        for status_code in [400, 404, 429, 500]:
            response = mock_free_companies_response(HOSTNAME, status_code, WORLD_NAME)
            responses.add(response)
            self.assertRaises(
                LodestoneScraperException,
                lambda: self.scraper.search_free_companies(WORLD_NAME),
            )
