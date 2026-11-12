"""Unit tests for ResumeParser with boundary safety and heuristic grade analysis."""

from hirify_mcp.parsing.resume import ResumeParser


def test_extract_skills_boundary_and_symbols():
    text = "Стек: C++, C#, .NET, Python, Docker, PostgreSQL."
    skills = ResumeParser.extract_skills(text)
    assert "c++" in skills
    assert "c#" in skills
    assert ".net" in skills
    assert "python" in skills
    assert "docker" in skills
    assert "postgresql" in skills


def test_extract_skills_no_false_substrings():
    # Django must not trigger 'go'
    text1 = "Опыт с Django и JavaScript"
    skills1 = ResumeParser.extract_skills(text1)
    assert "django" in skills1
    assert "javascript" in skills1
    assert "go" not in skills1
    assert "java" not in skills1

    # Standalone 'go' must trigger 'go'
    text2 = "Пишу на Go и Python"
    skills2 = ResumeParser.extract_skills(text2)
    assert "go" in skills2
    assert "python" in skills2


def test_extract_skills_react_and_react_native():
    text = "Разрабатываю на React Native и Node.js"
    skills = ResumeParser.extract_skills(text)
    assert "react native" in skills
    assert "nodejs" in skills


def test_aspiration_grade_vs_current_grade():
    """Ensure 'Ищу Junior Python Developer, в будущем хочу стать Senior' is NOT detected as Senior."""
    text = "Ищу Junior Python Developer, в будущем хочу стать Senior."
    grade, exp_years, has_comm = ResumeParser.extract_grade_and_experience(text)
    assert grade == "junior"
    assert grade != "senior"


def test_no_commercial_experience_not_middle():
    """'Изучаю Python три года, коммерческого опыта нет' must NOT be classified as Middle."""
    text = "Изучаю Python три года, коммерческого опыта нет. Делал pet-проекты на FastAPI."
    grade, exp_years, has_comm = ResumeParser.extract_grade_and_experience(text)
    assert grade in ("junior", "trainee")
    assert grade != "middle"
    assert has_comm is False
    assert exp_years == 0.0


def test_calendar_years_not_experience():
    text = "Окончил университет в 2024 году, ищу первую стажировку."
    grade, exp_years, has_comm = ResumeParser.extract_grade_and_experience(text)
    assert grade in ("trainee", "junior", None)
    assert exp_years != 2024


def test_commercial_experience_senior():
    text = "Более 6 лет коммерческого опыта в бэкенд разработке на Python и Go."
    grade, exp_years, has_comm = ResumeParser.extract_grade_and_experience(text)
    assert grade == "senior"
    assert has_comm is True
    assert exp_years == 6.0


def test_extract_remote_only():
    text = "Junior Python разработчик, рассматриваю только удаленку."
    prefs = ResumeParser.extract_preferences(text)
    assert prefs["remote_only"] is True
    assert "remote" in prefs["work_formats"]


def test_extract_salary_and_currency():
    text1 = "Ожидания по зарплате от 1500 USD, удаленно."
    p1 = ResumeParser.extract_preferences(text1)
    assert p1["min_salary"] == 1500.0
    assert p1["currency"] == "USD"

    text2 = "Зарплата от 200 000 руб в месяц"
    p2 = ResumeParser.extract_preferences(text2)
    assert p2["min_salary"] == 200000.0
    assert p2["currency"] == "RUB"


def test_extract_english_and_country():
    text = "Живу в Германии, английский B2, ищу удаленную работу."
    prefs = ResumeParser.extract_preferences(text)
    assert prefs["english_level"] == "b2"
    assert prefs["current_country"] == "germany"


def test_full_parse_profile():
    text = (
        "Привет! Я Junior Python разработчик. "
        "Стек: Python, FastAPI, PostgreSQL, Docker, Redis. "
        "Только удаленка. Локация: Россия. Зарплата от 80 000 руб."
    )
    profile = ResumeParser.parse_profile(text)
    assert profile.grade == "junior"
    assert profile.remote_only is True
    assert "remote" in profile.work_formats
    assert "python" in profile.skills
    assert "fastapi" in profile.skills
    assert profile.current_country == "russia"
    assert profile.min_salary == 80000.0
    assert profile.currency == "RUB"
