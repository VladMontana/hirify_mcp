"""Live integration tests for the MCP Server entry points and tools."""

import json

import pytest

from hirify_mcp.server import (
    get_vacancy_details,
    match_vacancies,
    parse_profile,
    search_vacancies,
)

pytestmark = pytest.mark.integration


def test_parse_profile_tool():
    text = "Senior Frontend Developer, React, TypeScript, Next.js, Redux, remote only"
    raw_json = parse_profile(text)
    data = json.loads(raw_json)
    assert data["grade"] == "senior"
    assert "react" in data["skills"]
    assert "typescript" in data["skills"]
    assert "remote" in data["work_formats"]


def test_search_vacancies_tool():
    result = search_vacancies(query="python", limit=3)
    assert "Найдено" in result
    assert "https://hirify.me/jobs/" in result


def test_get_vacancy_details_tool():
    from hirify_mcp.scraper import HirifyScraper

    scraper = HirifyScraper()
    vacs = scraper.search_vacancies(query="python", limit=1)
    assert len(vacs) > 0
    vac_id = vacs[0].id

    details_str = get_vacancy_details(vac_id)
    assert f"# {vacs[0].title}" in details_str or "Компания" in details_str


def test_match_vacancies_tool():
    resume = (
        "Middle Python Developer, 3 года опыта. "
        "Стек: Python, FastAPI, PostgreSQL, Docker. "
        "Формат: remote (удаленка)."
    )
    res = match_vacancies(resume, top_n=3, min_score=30)
    assert "Топ-" in res
    assert "Распознанный профиль соискателя:" in res
    assert "python" in res


def test_match_vacancies_role_based():
    resume = "QA Automation инженер, опыт 3 года, pytest, selenium, remote"
    res = match_vacancies(resume, top_n=3, min_score=20)
    assert "Распознанный профиль соискателя:" in res
    assert "qa" in res or "pytest" in res
