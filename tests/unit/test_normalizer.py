"""Unit tests for normalizer module."""

from hirify_mcp.parsing.normalizer import (
    normalize_currency,
    normalize_grade,
    normalize_skill,
    normalize_work_format,
    role_to_hirify_spec,
)


def test_normalize_skill_canonical():
    assert normalize_skill("postgres") == "postgresql"
    assert normalize_skill("pgsql") == "postgresql"
    assert normalize_skill("golang") == "go"
    assert normalize_skill("k8s") == "kubernetes"
    assert normalize_skill("node.js") == "nodejs"
    assert normalize_skill("node") == "nodejs"
    assert normalize_skill("docker-compose") == "docker-compose"
    assert normalize_skill("docker compose") == "docker-compose"
    assert normalize_skill("nextjs") == "next.js"
    assert normalize_skill("vue.js") == "vue"
    assert normalize_skill("python") == "python"


def test_normalize_grade():
    assert normalize_grade("intern") == "trainee"
    assert normalize_grade("стажер") == "trainee"
    assert normalize_grade("junior") == "junior"
    assert normalize_grade("джун") == "junior"
    assert normalize_grade("middle") == "middle"
    assert normalize_grade("мидл") == "middle"
    assert normalize_grade("senior") == "senior"
    assert normalize_grade("сеньор") == "senior"
    assert normalize_grade("lead") == "lead"
    assert normalize_grade("тимлид") == "lead"
    assert normalize_grade("head of") == "head"
    assert normalize_grade(None) is None


def test_normalize_work_format():
    assert normalize_work_format("remote") == "remote"
    assert normalize_work_format("удаленка") == "remote"
    assert normalize_work_format("hybrid") == "hybrid"
    assert normalize_work_format("гибрид") == "hybrid"
    assert normalize_work_format("onsite") == "onsite"
    assert normalize_work_format("офис") == "onsite"
    assert normalize_work_format("неизвестно") is None


def test_normalize_currency():
    assert normalize_currency("$") == "USD"
    assert normalize_currency("usd") == "USD"
    assert normalize_currency("руб") == "RUB"
    assert normalize_currency("₽") == "RUB"
    assert normalize_currency("eur") == "EUR"
    assert normalize_currency("€") == "EUR"
    assert normalize_currency("kzt") == "KZT"
    assert normalize_currency(None) is None


def test_role_to_hirify_spec():
    assert role_to_hirify_spec("backend") == "backend_dev"
    assert role_to_hirify_spec("frontend") == "frontend_dev"
    assert role_to_hirify_spec("fullstack") == "fullstack_dev"
    assert role_to_hirify_spec("devops") == "devops"
    assert role_to_hirify_spec("qa") == "qa_automation"
    assert role_to_hirify_spec("data_engineering") == "data_engineering"
    assert role_to_hirify_spec("data_engineer") == "data_engineering"
    assert role_to_hirify_spec("data_science") == "data_science"
    assert role_to_hirify_spec("ai_engineering") == "ai_engineering"
    assert role_to_hirify_spec("cybersecurity") == "cybersecurity"
    assert role_to_hirify_spec("unknown_role") is None
