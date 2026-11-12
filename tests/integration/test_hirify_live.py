"""Live integration tests against the actual Hirify API.

Run only when network is available:
    pytest -m integration
"""

import pytest

from hirify_mcp.clients.hirify import HirifyClient


@pytest.mark.integration
def test_live_hirify_search_vacancies():
    client = HirifyClient()
    vacancies = client.search_vacancies(query="python", limit=5)
    assert isinstance(vacancies, list)
    assert len(vacancies) > 0
    first = vacancies[0]
    assert first.id > 0
    assert first.title
    assert "https://hirify.me/jobs/" in first.url


@pytest.mark.integration
def test_live_hirify_vacancy_details():
    client = HirifyClient()
    vacancies = client.search_vacancies(query="python", limit=1)
    assert len(vacancies) > 0
    vac_id = vacancies[0].id

    details = client.get_vacancy_details(vac_id)
    assert details is not None
    assert details.id == vac_id
    assert details.title


@pytest.mark.integration
def test_live_hirify_pagination():
    client = HirifyClient()
    # Limit 20 forces fetching 2 pages (15 + 5)
    vacancies = client.search_vacancies(query="python", limit=20)
    assert len(vacancies) > 15
