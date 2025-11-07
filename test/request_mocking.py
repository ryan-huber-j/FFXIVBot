import responses

from domain import FreeCompanyRanking
from lodestone import GrandCompanyRanking


def fake_member_entry(member):
    return f"""
    <li class='entry'><a href='/lodestone/character/{member.ffxiv_id}/' class='entry__bg'>
      <div class='entry__flex'>
        <div class='entry__freecompany__center'><p class='entry__name'>{member.name}</p>
          <ul class='entry__freecompany__info'>
            <li><img src='img-url' width='20'
                    height='20' alt=''><span>{member.rank}</span></li>
          </ul>
        </div>
      </div>
    </a></li>
  """


def mock_fc_members_response(hostname, status, fc_id, members=None, page=1, max_pages=1):
    query = f"?page={page}" if page > 1 else ""
    url = f"https://{hostname}/lodestone/freecompany/{fc_id}/member{query}"
    matchers = (
        [responses.matchers.query_param_matcher({"page": str(page)})] if page > 1 else []
    )

    if members is not None:
        member_entries = "\n".join(fake_member_entry(member) for member in members)
        body = f"""
    <body>
      <ul class='btn__pager'>
        <li class='btn__pager__current'>Page {page} of {max_pages}</li>
      </ul>
      <ul>
        {member_entries}
      </ul>
    </body>
    """
    else:
        body = ""

    return responses.Response(
        responses.GET, url, body=body, status=status, match=matchers
    )


def fake_gc_ranking_row(ranking: GrandCompanyRanking):
    return f"""
    <tr data-href='/lodestone/character/{ranking.character_id}/' class='clickable'>
      <td class='ranking-character__number											'> {ranking.rank} </td>
      <td class='ranking-character__face'> <img
          src='https://img2.finalfantasyxiv.com/f/ba64ef52323ad0c23edaa3bafc9f4e82_58a84e851e55175d22158ca97af58a1ffc0_96x96.jpg?1702063037'
          width='50' height='50' alt=''> </td>
      <td class='ranking-character__info'>
        <h4>{ranking.character_name}</h4>
        <p><i class='xiv-lds xiv-lds-home-world js__tooltip' data-tooltip='Home World'></i>Siren [Aether]</p>
      </td>
      <td class='ranking-character__gcrank'> <img
          src='https://lds-img.finalfantasyxiv.com/h/V/tKlwWMAtNLAumnqjI8iNPnMKHc.png' width='32' height='32'
          alt='Immortal Flames/Flame Captain' class='js__tooltip' data-tooltip='Immortal Flames/Flame Captain'> </td>
      <td class='ranking-character__value'> {ranking.seals} </td>
    </tr>
  """


def mock_gc_rankings_response(hostname, status, world, rankings, page_num):
    if rankings is None:
        body = ""
    else:
        ranking_rows = "\n".join(fake_gc_ranking_row(ranking) for ranking in rankings)
        body = f"""
      <table>
        <tbody>
          {ranking_rows}
        </tbody>
      </table>
    """

    url = f"https://{hostname}/lodestone/ranking/gc/weekly?page={page_num}&worldname={world}"
    return responses.Response(
        responses.GET, url, body=body, status=status, content_type="text/html"
    )


def register_gc_pages(hostname, world, rankings, status=200, pages=5):
    responses.add(mock_gc_rankings_response(hostname, status, world, rankings, 1))
    for p in range(2, pages + 1):
        responses.add(mock_gc_rankings_response(hostname, status, world, [], p))


def register_gc_page(hostname, world, rankings, page_num=1, status=200):
    responses.add(mock_gc_rankings_response(hostname, status, world, rankings, page_num))


def register_empty_gc_pages(hostname, world, start_page=2, pages=5, status=200):
    for p in range(start_page, pages + 1):
        responses.add(mock_gc_rankings_response(hostname, status, world, [], p))


def mock_free_companies_response(hostname, status_code, world, fcs=[]):
    key = f"https://{hostname}/lodestone/freecompany?worldname={world}"

    fc_html_elems = []
    for free_company in fcs:
        html = f"""
      <div class='entry'>
        <a href='/lodestone/freecompany/{free_company.id}/' class='entry__block'>
          <div class='entry__freecompany__inner'>
            <div class='entry__freecompany__box'>
              <p class='entry__world'>Maelstrom</p>
              <p class='entry__name'>{free_company.name}</p>
              <p class='entry__world'><i class='xiv-lds xiv-lds-home-world js__tooltip' data-tooltip='Home World'></i>{world}
                [Aether]</p>
            </div>
          </div>
          <ul class='entry__freecompany__fc-data clearix'>
            <li class='entry__freecompany__fc-member'>35</li>
            <li class='entry__freecompany__fc-housing'>Estate Built</li>
            <li class='entry__freecompany__fc-day'><span id='datetime-f106dabe182'>09/20/2021</span>
              <script>document.getElementById('datetime-f106dabe182').innerHTML = ldst_strftime(1632175472, 'YMD');</script>
            </li>
            <li class='entry__freecompany__fc-active'>Active: Always</li>
            <li class='entry__freecompany__fc-active'>Recruitment: Open</li>
          </ul>
        </a>
      </div>
    """
        fc_html_elems.append(html)

    body = f"""
    <div>
      {''.join(fc_html_elems)}
    </div>
  """

    return responses.Response(
        responses.GET, key, body=body, status=status_code, content_type="text/html"
    )


def register_fc_members(hostname, fc_id, members, status=200, page=1, max_pages=1):
    responses.add(
        mock_fc_members_response(
            hostname, status, fc_id, members=members, page=page, max_pages=max_pages
        )
    )


def fake_fc_ranking_row(ranking: FreeCompanyRanking):
    return f"""
    <tr data-href='/lodestone/freecompany/{ranking.ffxiv_id}/' class='clickable'>
      <td class="ranking-character__number ranking-character__up">{ranking.rank}</td>
      <td class='ranking-character__info ranking-character__info-freecompany'>
        <h4>{ranking.name}</h4>
      </td>
      <td class='ranking-character__value'>{ranking.seals_earned}</td>
    </tr>
  """


def mock_fc_ranking_response(hostname, status_code, data_center, rankings):
    if rankings is None:
        body = ""
    else:
        ranking_rows = "\n".join(fake_fc_ranking_row(ranking) for ranking in rankings)
        body = f"""
          <table class="ranking-character ranking-character__freecompany js--ranking" cellpadding="0" cellspacing="0">
            <tbody>
              {ranking_rows}
              </tr>
            </tbody>
          </table>
        """

    url = f"https://{hostname}/lodestone/ranking/fc/weekly?filter=1&dcgroup={data_center}&dcGroup={data_center}"
    return responses.Response(
        responses.GET, url, body=body, status=status_code, content_type="text/html"
    )


def register_fc_rankings(hostname, data_center, rankings, status=200):
    responses.add(mock_fc_ranking_response(hostname, status, data_center, rankings))
