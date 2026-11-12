"""Integration and contract tests for Hirify Scraper using Scrapling."""

from hirify_mcp.scraper import HirifyScraper


def test_scraper_search_vacancies():
    scraper = HirifyScraper()
    vacancies = scraper.search_vacancies(query="python", limit=5)
    assert isinstance(vacancies, list)
    assert len(vacancies) > 0
    first = vacancies[0]
    assert first.id > 0
    assert first.title
    assert "https://hirify.me/jobs/" in first.url


def test_scraper_get_details():
    scraper = HirifyScraper()
    vacancies = scraper.search_vacancies(query="python", limit=1)
    assert len(vacancies) > 0
    vac_id = vacancies[0].id
    details = scraper.get_vacancy_details(vac_id)
    assert details is not None
    assert details.id == vac_id
    assert details.title


def test_scraper_query_encoding_and_pagination():
    scraper = HirifyScraper()
    # Test query with special characters ('c++')
    vacancies = scraper.search_vacancies(query="c++", limit=3)
    assert isinstance(vacancies, list)

    # Test limit > 15 (triggers multi-page pagination)
    vacancies_large = scraper.search_vacancies(query="python", limit=20)
    assert isinstance(vacancies_large, list)
    assert len(vacancies_large) > 15
