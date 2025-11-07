import re

from bs4 import BeautifulSoup
from cachetools import TTLCache, cached
import requests

from domain import FCMember, FreeCompany, FreeCompanyRanking, GrandCompanyRanking

_page_number_regex = re.compile("Page \d of (\d)")
_character_link_regex = re.compile("/lodestone/character/(.+)/")
_fc_link_regex = re.compile("/lodestone/freecompany/(.+)/")


class LodestoneScraperException(Exception):
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class LodestoneScraper:
    def __init__(self, base_url: str):
        self._base_url = base_url

    def _get_fc_members_page(self, fc_id: str, page_num: int = None):
        if page_num is None:
            url = f"{self._base_url}/lodestone/freecompany/{fc_id}/member"
        else:
            url = f"{self._base_url}/lodestone/freecompany/{fc_id}/member?page={page_num}"

        response = requests.get(url)

        if response.status_code == 404:
            raise LodestoneScraperException(
                f"Free Company {fc_id} could not be found", response.status_code
            )
        elif response.status_code == 429:
            raise LodestoneScraperException(
                f"Unable to fetch Free Company members due to Lodestone rate limiting"
            )
        elif response.status_code >= 400 and response.status_code < 500:
            raise LodestoneScraperException(
                f"Failed to access FC {fc_id} members due to an unknown client error",
                response.status_code,
            )
        elif response.status_code >= 500:
            raise LodestoneScraperException(
                "The Lodestone appears to be down", response.status_code
            )
        elif response.status_code != 200:
            raise LodestoneScraperException(
                f"Failed to access FC {fc_id} members due to an unknown issue",
                response.status_code,
            )

        return response

    def _scrape_members_from_page(self, page: BeautifulSoup):
        fc_members = []

        member_list_items_tags = page.find_all("li", class_="entry")
        for member_tag in member_list_items_tags:
            character_link_tag = member_tag.find("a", class_="entry__bg")
            character_link = character_link_tag["href"]
            lodestone_id_match = _character_link_regex.fullmatch(character_link)
            if lodestone_id_match is None:
                raise LodestoneScraperException(
                    f"Unable to parse character lodestone ID from following: {character_link}"
                )
            lodestone_id = lodestone_id_match.group(1)

            member_name = member_tag.find("p", class_="entry__name").string

            member_fc_info_tag = member_tag.find("ul", class_="entry__freecompany__info")
            member_rank = member_fc_info_tag.find("li").find("span").string

            fc_members.append(FCMember(lodestone_id, member_name, member_rank))

        return fc_members

    @cached(cache=TTLCache(maxsize=100, ttl=300))
    def get_free_company_members(self, fc_id: str) -> list[FCMember]:
        response = self._get_fc_members_page(fc_id)
        page = BeautifulSoup(response.content, "html.parser")

        page_number_tag = page.find("li", class_="btn__pager__current")
        match = _page_number_regex.fullmatch(page_number_tag.string)
        if match is None:
            raise LodestoneScraperException(
                f"Unable to parse page number from following: {page_number_tag.string}"
            )
        num_pages = int(match.group(1))

        members = self._scrape_members_from_page(page)
        for page_num in range(2, num_pages + 1):
            response = self._get_fc_members_page(fc_id, page_num)
            page = BeautifulSoup(response.content, "html.parser")
            members += self._scrape_members_from_page(page)

        return members

    @cached(cache=TTLCache(maxsize=100, ttl=300))
    def get_grand_company_rankings(self, world: str) -> list[GrandCompanyRanking]:
        rankings = []

        for page_num in range(1, 6):
            response = requests.get(
                f"{self._base_url}/lodestone/ranking/gc/weekly?page={page_num}&worldname={world}"
            )

            if response.status_code == 404:
                raise LodestoneScraperException(
                    f"Could not find Grand Company rankings for {world}",
                    response.status_code,
                )
            elif response.status_code == 429:
                raise LodestoneScraperException(
                    f"Unable to fetch Grand Company rankings due to Lodestone rate limiting"
                )
            elif response.status_code >= 400 and response.status_code < 500:
                raise LodestoneScraperException(
                    f"Could not find Grand Company rankings due to an unknown client error",
                    response.status_code,
                )
            elif response.status_code >= 500:
                raise LodestoneScraperException(
                    "The Lodestone appears to be down", response.status_code
                )
            elif response.status_code != 200:
                raise LodestoneScraperException(
                    f"Could not find Grand Company rankings due to an unknown issue",
                    response.status_code,
                )

            page = BeautifulSoup(response.content, "html.parser")

            ranking_table_row_tags = page.select("tbody tr")
            for ranking_row_tag in ranking_table_row_tags:
                id = str(ranking_row_tag["data-href"]).split("/")[3]
                name = str(ranking_row_tag.find("h4").contents[0]).strip()
                ranking = int(
                    str(
                        ranking_row_tag.select(".ranking-character__number")[0].text
                    ).strip()
                )
                seals = int(
                    str(
                        ranking_row_tag.find(
                            "td", {"class": "ranking-character__value"}
                        ).text
                    ).strip()
                )
                rankings.append(GrandCompanyRanking(id, name, ranking, seals))

        return rankings

    @cached(cache=TTLCache(maxsize=100, ttl=300))
    def search_free_companies(self, world: str) -> list[FreeCompany]:
        response = requests.get(
            f"{self._base_url}/lodestone/freecompany?worldname={world}"
        )

        if response.status_code == 404:
            raise LodestoneScraperException(
                f"Could not find Free Companies for {world}", response.status_code
            )
        elif response.status_code == 429:
            raise LodestoneScraperException(
                f"Unable to fetch Free Companies due to Lodestone rate limiting"
            )
        elif response.status_code >= 400 and response.status_code < 500:
            raise LodestoneScraperException(
                f"Could not find Free Companies due to an unknown client error",
                response.status_code,
            )
        elif response.status_code >= 500:
            raise LodestoneScraperException(
                "The Lodestone appears to be down", response.status_code
            )
        elif response.status_code != 200:
            raise LodestoneScraperException(
                f"Could not find Free Companies due to an unknown issue",
                response.status_code,
            )

        page = BeautifulSoup(response.content, "html.parser")
        fc_entry_tags = page.find_all("div", class_="entry")
        free_companies = []
        for fc_entry in fc_entry_tags:
            fc_link_tag = fc_entry.find("a", class_="entry__block")
            lodestone_id_match = _fc_link_regex.fullmatch(fc_link_tag["href"])
            lodestone_id = lodestone_id_match.group(1)
            free_company_name = fc_entry.find("p", class_="entry__name").string
            free_companies.append(FreeCompany(lodestone_id, free_company_name))

        return free_companies

    @cached(cache=TTLCache(maxsize=100, ttl=300))
    def get_top_100_free_company_rankings(
        self, data_center: str
    ) -> list[FreeCompanyRanking]:
        response = requests.get(
            f"{self._base_url}/lodestone/ranking/fc/weekly?filter=1&dcgroup={data_center}&dcGroup={data_center}"
        )

        if response.status_code == 404:
            raise LodestoneScraperException(
                f"Could not find Free Company rankings for data center {data_center}",
                response.status_code,
            )
        elif response.status_code == 429:
            raise LodestoneScraperException(
                f"Unable to fetch Free Company rankings due to Lodestone rate limiting"
            )
        elif response.status_code >= 400 and response.status_code < 500:
            raise LodestoneScraperException(
                f"Could not find Free Company rankings due to an unknown client error",
                response.status_code,
            )
        elif response.status_code >= 500:
            raise LodestoneScraperException(
                "The Lodestone appears to be down", response.status_code
            )
        elif response.status_code != 200:
            raise LodestoneScraperException(
                f"Could not find Free Company rankings due to an unknown issue",
                response.status_code,
            )

        page = BeautifulSoup(response.content, "html.parser")
        ranking_table_row_tags = page.find("table", class_="ranking-character").find_all(
            "tr"
        )
        rankings = []
        for ranking_row_tag in ranking_table_row_tags:
            id = str(ranking_row_tag["data-href"]).split("/")[3]
            name = str(ranking_row_tag.find("h4").contents[0]).strip()
            ranking = int(ranking_row_tag.select(".ranking-character__number")[0].text)
            seals_earned = int(
                ranking_row_tag.find("td", {"class": "ranking-character__value"}).text
            )
            rankings.append(FreeCompanyRanking(id, name, ranking, seals_earned))

        return rankings
