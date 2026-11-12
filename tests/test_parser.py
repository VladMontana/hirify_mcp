"""Unit tests for candidate profile and resume parser."""

from hirify_mcp.parser import ResumeParser


def test_extract_skills_from_text():
    text = """
    Привет! Я Senior Python разработчик.
    Основной стек: Python, FastAPI, Django, PostgreSQL, Redis, Docker, Celery.
    Также работал с Kubernetes (k8s), AWS и Kafka.
    """
    skills = ResumeParser.extract_skills(text)
    assert "python" in skills
    assert "fastapi" in skills
    assert "django" in skills
    assert "postgresql" in skills
    assert "redis" in skills
    assert "docker" in skills
    assert "celery" in skills
    assert "kubernetes" in skills
    assert "aws" in skills
    assert "kafka" in skills


def test_extract_grade_explicit():
    assert ResumeParser.extract_grade("Middle backend developer") == "middle"
    assert ResumeParser.extract_grade("Senior Data Scientist") == "senior"
    assert ResumeParser.extract_grade("Ищу позицию джуниор разработчика") == "junior"
    assert ResumeParser.extract_grade("TeamLead Golang команды") == "lead"
    assert ResumeParser.extract_grade("Работал старшим разработчиком 5 лет") == "senior"


def test_extract_grade_from_years():
    assert ResumeParser.extract_grade("Опыт работы более 6 лет в разработке") == "senior"
    assert ResumeParser.extract_grade("3 года опыта с Python/Django") == "middle"
    assert ResumeParser.extract_grade("1 год опыта") == "junior"
    assert ResumeParser.extract_grade("1.5 года опыта") == "junior"
    assert ResumeParser.extract_grade("2.5 года коммерческого опыта") == "middle"
    # Calendar graduation year must NOT be treated as senior
    assert ResumeParser.extract_grade("В 2023 году окончил университет, ищу первую работу") is None


def test_extract_skills_delimiters():
    text = "Стек: Python: FastAPI; Docker! (PostgreSQL) [Redis] 'Kafka' \"AWS\""
    skills = ResumeParser.extract_skills(text)
    assert "python" in skills
    assert "fastapi" in skills
    assert "docker" in skills
    assert "postgresql" in skills
    assert "redis" in skills
    assert "kafka" in skills
    assert "aws" in skills


def test_extract_work_formats():
    assert "remote" in ResumeParser.extract_work_formats("Ищу только удаленку")
    assert "hybrid" in ResumeParser.extract_work_formats("Рассматриваю гибридный график")
    assert "onsite" in ResumeParser.extract_work_formats("Готов работать в офисе")


def test_parse_profile_full():
    raw_text = (
        "Привет, я сеньор бэкенд разработчик. "
        "Стек: Python, FastAPI, PostgreSQL, Docker, Redis. "
        "Интересует удаленная работа."
    )
    profile = ResumeParser.parse_profile(raw_text)
    assert profile.grade == "senior"
    assert "backend" in profile.roles
    assert "remote" in profile.work_formats
    assert "python" in profile.skills
    assert "fastapi" in profile.skills
    assert "postgresql" in profile.skills
    assert "docker" in profile.skills
    assert "redis" in profile.skills


def test_empty_text():
    profile = ResumeParser.parse_profile("")
    assert profile.skills == []
    assert profile.grade is None
    assert profile.roles == []
    assert profile.work_formats == []
