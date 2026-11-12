"""Unit tests for matcher and scoring engine."""

from hirify_mcp.matcher import VacancyMatcher
from hirify_mcp.models import CandidateProfile, GradeItem, TagItem, VacancySummary


def test_score_skills_full_match():
    cand_skills = ["python", "fastapi", "docker", "postgresql"]
    vac_skills = ["python", "fastapi"]
    score, matched, missing = VacancyMatcher.score_skills(cand_skills, vac_skills)
    assert score == 65.0
    assert matched == ["fastapi", "python"]
    assert missing == []


def test_score_skills_partial_match():
    cand_skills = ["python", "docker"]
    vac_skills = ["python", "fastapi", "kubernetes", "postgresql"]
    score, matched, missing = VacancyMatcher.score_skills(cand_skills, vac_skills)
    # 1 of 4 matched => 65.0 / 4 = 16.25
    assert score == 16.25
    assert matched == ["python"]
    assert "fastapi" in missing


def test_score_grade():
    score, match_type = VacancyMatcher.score_grade("senior", ["senior"])
    assert score == 20.0
    assert match_type == "exact"

    score_close, match_close = VacancyMatcher.score_grade("senior", ["middle"])
    assert score_close == 12.0
    assert match_close == "close"

    score_mis, match_mis = VacancyMatcher.score_grade("senior", ["junior"])
    assert score_mis == 4.0
    assert match_mis == "mismatch"


def test_score_format():
    score, matched = VacancyMatcher.score_format(["remote"], ["remote", "hybrid"])
    assert score == 15.0
    assert matched is True

    score_mis, matched_mis = VacancyMatcher.score_format(["remote"], ["onsite"])
    assert score_mis == 0.0
    assert matched_mis is False


def test_match_single_vacancy():
    profile = CandidateProfile(
        raw_text="Senior Python dev",
        skills=["python", "fastapi", "docker", "postgresql"],
        grade="senior",
        work_formats=["remote"],
    )
    vacancy = VacancySummary(
        id=123,
        title="Senior Python Backend Developer",
        company_title="TechCorp",
        work_format=["remote"],
        tags=[TagItem(name="python"), TagItem(name="fastapi"), TagItem(name="docker")],
        grades=[GradeItem(name="senior")],
    )

    res = VacancyMatcher.match(profile, vacancy)
    assert res.total_score >= 90
    assert res.grade_match == "exact"
    assert res.format_match is True
    assert "python" in res.matched_skills
    assert "fastapi" in res.matched_skills


def test_extract_vacancy_skills_no_false_substring_matches():
    """Ensure 'Django' doesn't match 'go', 'JavaScript' doesn't match 'java'."""
    v1 = VacancySummary(id=1, title="Django Developer")
    skills1 = VacancyMatcher._extract_vacancy_skills(v1)
    assert "django" in skills1
    assert "go" not in skills1

    v2 = VacancySummary(id=2, title="JavaScript Developer")
    skills2 = VacancyMatcher._extract_vacancy_skills(v2)
    assert "javascript" in skills2
    assert "java" not in skills2


def test_canonical_tag_matching():
    """Ensure postgresql/postgres and go/golang match seamlessly."""
    p_pg = CandidateProfile(raw_text="dev", skills=["postgresql"])
    v_pg = VacancySummary(id=10, title="Dev", tags=[TagItem(name="postgres")])
    res_pg = VacancyMatcher.match(p_pg, v_pg)
    assert "postgresql" in res_pg.matched_skills
    assert res_pg.missing_skills == []

    p_go = CandidateProfile(raw_text="dev", skills=["go"])
    v_go = VacancySummary(id=20, title="Dev", tags=[TagItem(name="golang")])
    res_go = VacancyMatcher.match(p_go, v_go)
    assert "go" in res_go.matched_skills
    assert res_go.missing_skills == []


def test_salary_parsing_and_display():
    from hirify_mcp.models import SalaryItem

    vacancy = VacancySummary(
        id=99,
        title="Python Dev",
        salary=SalaryItem(min=100000, max=150000, currency="RUB"),
    )
    assert vacancy.salary_display == "100 000 - 150 000 RUB"

    profile = CandidateProfile(raw_text="Python dev", skills=["python"])
    res = VacancyMatcher.match(profile, vacancy)
    assert res.salary == "100 000 - 150 000 RUB"
