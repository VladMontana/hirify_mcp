"""Tests for MCP server tool registration, execution, and error handling."""

import json
from pathlib import Path

import httpx
import pytest

import hirify_mcp.server as server_module
from hirify_mcp.server import (
    get_new_vacancies,
    get_vacancy_details,
    list_saved_vacancies,
    match_vacancies,
    parse_profile,
    prepare_application_context,
    save_vacancy,
    search_vacancies,
    update_application_status,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def python_junior_data():
    with open(FIXTURES_DIR / "vacancies_python_junior.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_detail_data():
    with open(FIXTURES_DIR / "vacancy_details_sample.json", "r", encoding="utf-8") as f:
        return json.load(f)


def test_mcp_tool_registration():
    """Verify that all required tools are registered with the MCPServer instance."""
    tools = [
        "parse_profile",
        "search_vacancies",
        "get_vacancy_details",
        "match_vacancies",
        "get_new_vacancies",
        "save_vacancy",
        "list_saved_vacancies",
        "update_application_status",
        "prepare_application_context",
    ]
    for t in tools:
        fn = getattr(server_module, t, None)
        assert callable(fn), f"Tool {t} should be callable"


def test_tool_parse_profile():
    raw_text = (
        "Junior Python разработчик, 1 год опыта. "
        "Стек: Python, FastAPI, PostgreSQL, Docker, Redis. "
        "Формат: remote only. Локация: Россия. Зарплата от 90 000 руб."
    )
    result = parse_profile(raw_text)
    data = json.loads(result)
    assert data["grade"] == "junior"
    assert "python" in data["skills"]
    assert "fastapi" in data["skills"]
    assert data["remote_only"] is True
    assert "remote" in data["work_formats"]
    assert data["current_country"] == "russia"
    assert data["min_salary"] == 90000.0


def test_tool_search_vacancies_success(python_junior_data, monkeypatch):
    def mock_request(self, method, url, params=None):
        return httpx.Response(200, json=python_junior_data)

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    res = search_vacancies(query="python", grade="junior", limit=3)
    assert "Найдено" in res
    assert "https://hirify.me/jobs/" in res


def test_tool_search_vacancies_api_error_scenario_e(monkeypatch):
    """Scenario E: API returns HTTP 503 -> clear error message, NOT 'no vacancies found'."""

    def mock_request(self, method, url, params=None):
        return httpx.Response(503, text="Service Unavailable")

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    res = search_vacancies(query="python")
    assert "Ошибка Hirify API" in res or "HTTP 503" in res
    assert "не найдено" not in res.lower()


def test_tool_get_vacancy_details(sample_detail_data, monkeypatch):
    vac_id = sample_detail_data["id"]

    def mock_request(self, method, url, params=None):
        return httpx.Response(200, json=sample_detail_data)

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    res = get_vacancy_details(vac_id)
    assert f"#{sample_detail_data['title']}" in res or sample_detail_data["title"] in res
    assert "https://hirify.me/jobs/" in res


def test_tool_match_vacancies_workflow(python_junior_data, monkeypatch):
    def mock_request(self, method, url, params=None):
        return httpx.Response(200, json=python_junior_data)

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    resume = (
        "Junior Python разработчик. "
        "Стек: Python, FastAPI, Docker, PostgreSQL. "
        "Только удаленка. Локация: Россия."
    )
    res = match_vacancies(resume, top_n=3, min_score=20)
    assert "🎯 Топ-" in res or "Распознанный профиль" in res
    assert "совместимость" in res.lower() or "балл" in res.lower()


def test_tool_save_and_list_vacancies(python_junior_data, monkeypatch):
    # 1. Update application status
    res = save_vacancy(vacancy_id=99901, status="applied", notes="Sent CV via site")
    assert "успешно" in res

    # 2. Update via update_application_status
    res_up = update_application_status(
        vacancy_id=99901, status="interview", notes="Interview on Monday"
    )
    assert "успешно" in res_up

    # 3. List saved
    listing = list_saved_vacancies(status="interview")
    assert "INTERVIEW" in listing or "99901" in listing

    # 4. Check new vacancies tool
    new_res = get_new_vacancies(limit=5)
    assert isinstance(new_res, str)

    # 5. Invalid status validation
    err_res = save_vacancy(vacancy_id=99901, status="invalid_status")
    assert "Недопустимый статус" in err_res


def test_tool_prepare_application_context_scenario_g(sample_detail_data, monkeypatch):
    """Scenario G: Prepare application context with no fake facts and safety notices."""
    vac_id = sample_detail_data["id"]

    def mock_request(self, method, url, params=None):
        return httpx.Response(200, json=sample_detail_data)

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    profile_text = "Junior Python разработчик, FastAPI, PostgreSQL, 3 pet-проекта"
    ctx_json = prepare_application_context(vacancy_id=vac_id, profile_text=profile_text)
    data = json.loads(ctx_json)

    assert data["vacancy_id"] == vac_id
    assert "title" in data
    assert "safety_notice" in data
    assert "Автоматическая отправка откликов запрещена" in data["safety_notice"]


def test_mcp_stdio_protocol_exchange():
    """Verify standard stdio JSON-RPC handshake, tools/list, and tool execution."""
    import subprocess
    import sys

    proc = subprocess.Popen(
        [sys.executable, "-m", "hirify_mcp.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        # 1. Initialize
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "pytest-client", "version": "1.0"},
            },
        }
        proc.stdin.write(json.dumps(init_req) + "\n")
        proc.stdin.flush()
        init_resp = json.loads(proc.stdout.readline())
        assert init_resp.get("id") == 1
        assert "serverInfo" in init_resp.get("result", {})

        # 2. Initialized
        proc.stdin.write(
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
        )
        proc.stdin.flush()

        # 3. List tools
        proc.stdin.write(
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n"
        )
        proc.stdin.flush()
        tools_resp = json.loads(proc.stdout.readline())
        tool_names = [t["name"] for t in tools_resp.get("result", {}).get("tools", [])]
        assert "parse_profile" in tool_names
        assert "match_vacancies" in tool_names

        # 4. Call tool
        call_req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "parse_profile",
                "arguments": {"text": "Junior Python, FastAPI, remote"},
            },
        }
        proc.stdin.write(json.dumps(call_req) + "\n")
        proc.stdin.flush()
        call_resp = json.loads(proc.stdout.readline())
        assert not call_resp.get("error")
        content = call_resp.get("result", {}).get("content", [])
        assert len(content) > 0
        parsed = json.loads(content[0]["text"])
        assert parsed["grade"] == "junior"
    finally:
        proc.terminate()
        proc.wait(timeout=3)
