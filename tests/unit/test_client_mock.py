"""Offline deterministic tests for HirifyClient using fixtures and mocked responses."""

import json
from pathlib import Path

import httpx
import pytest

from hirify_mcp.clients.exceptions import (
    HirifyAPIError,
    HirifyRateLimitError,
    HirifyResponseError,
    HirifyTimeoutError,
)
from hirify_mcp.clients.hirify import HirifyClient

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def page1_data():
    with open(FIXTURES_DIR / "vacancies_page1.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def python_junior_data():
    with open(FIXTURES_DIR / "vacancies_python_junior.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def vacancy_detail_data():
    with open(FIXTURES_DIR / "vacancy_details_sample.json", "r", encoding="utf-8") as f:
        return json.load(f)


def test_client_search_success(page1_data, monkeypatch):
    """Test successful search using realistic fixture."""

    def mock_request(self, method, url, params=None):
        return httpx.Response(200, json=page1_data)

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = HirifyClient(enable_cache=False)
    results = client.search_vacancies(query="python", limit=5)
    assert len(results) == 5
    assert results[0].id > 0
    assert results[0].title
    assert results[0].url.startswith("https://hirify.me/jobs/")


def test_client_get_details_success(vacancy_detail_data, monkeypatch):
    vac_id = vacancy_detail_data["id"]

    def mock_request(self, method, url, params=None):
        return httpx.Response(200, json=vacancy_detail_data)

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = HirifyClient(enable_cache=False)
    details = client.get_vacancy_details(vac_id)
    assert details is not None
    assert details.id == vac_id
    assert details.title == vacancy_detail_data["title"]


def test_client_404_not_found(monkeypatch):
    def mock_request(self, method, url, params=None):
        return httpx.Response(404, text="Not Found")

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = HirifyClient(enable_cache=False)
    # get_vacancy_details returns None on 404
    details = client.get_vacancy_details(99999999)
    assert details is None


def test_client_429_rate_limit(monkeypatch):
    def mock_request(self, method, url, params=None):
        return httpx.Response(429, headers={"Retry-After": "1"}, text="Too Many Requests")

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = HirifyClient(max_retries=1, backoff_factor=0.01, enable_cache=False)
    with pytest.raises(HirifyRateLimitError) as exc_info:
        client.search_vacancies(query="python", limit=5)
    assert exc_info.value.status_code == 429


def test_client_503_server_error(monkeypatch):
    def mock_request(self, method, url, params=None):
        return httpx.Response(503, text="Service Unavailable")

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = HirifyClient(max_retries=1, backoff_factor=0.01, enable_cache=False)
    with pytest.raises(HirifyAPIError) as exc_info:
        client.search_vacancies(query="python", limit=5)
    assert exc_info.value.status_code == 503


def test_client_timeout(monkeypatch):
    def mock_request(self, method, url, params=None):
        raise httpx.ReadTimeout("Request timed out")

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = HirifyClient(max_retries=1, backoff_factor=0.01, enable_cache=False)
    with pytest.raises(HirifyTimeoutError):
        client.search_vacancies(query="python", limit=5)


def test_client_invalid_json(monkeypatch):
    def mock_request(self, method, url, params=None):
        return httpx.Response(200, text="<html><body>Gateway Error</body></html>")

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = HirifyClient(enable_cache=False)
    with pytest.raises(HirifyResponseError):
        client.search_vacancies(query="python", limit=5)


def test_client_ttl_caching(page1_data, monkeypatch):
    call_count = 0

    def mock_request(self, method, url, params=None):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=page1_data)

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = HirifyClient(enable_cache=True, cache_ttl=60)
    # First call: misses cache -> HTTP request executed
    res1 = client.search_vacancies(query="python", limit=5)
    assert call_count == 1

    # Second call: hits cache -> HTTP request NOT executed
    res2 = client.search_vacancies(query="python", limit=5)
    assert call_count == 1
    assert len(res1) == len(res2)


def test_client_pagination_stops_at_last_page(monkeypatch):
    # Mock single-page response with last_page = 1
    single_page = {
        "current_page": 1,
        "last_page": 1,
        "total": 3,
        "data": [
            {"id": 1, "title": "A"},
            {"id": 2, "title": "B"},
            {"id": 3, "title": "C"},
        ],
    }

    call_count = 0

    def mock_request(self, method, url, params=None):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=single_page)

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = HirifyClient(enable_cache=False)
    results = client.search_vacancies(query="test", limit=50)
    # Must stop after 1 page because current_page >= last_page
    assert call_count == 1
    assert len(results) == 3
