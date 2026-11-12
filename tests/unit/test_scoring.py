"""Unit tests for ScoringModel and MatchingEngine."""

from hirify_mcp.matching.engine import MatchingEngine
from hirify_mcp.matching.scoring import ScoringModel
from hirify_mcp.models import (
    CandidateProfile,
    GradeItem,
    SpecializationItem,
    TagItem,
    VacancySummary,
)


def test_scenario_d_vacancy_without_tags():
    """Scenario D: Vacancy with NO tags/stack must NOT get high score."""
    profile = CandidateProfile(
        raw_text="",
        skills=["python", "fastapi", "postgresql", "docker"],
        roles=["backend"],
        grade="junior",
    )
    vac_no_tags = VacancySummary(
        id=201,
        title="Developer",
        tags=[],
    )
    mand_score, opt_score, matched, missing, _ = ScoringModel.score_skills(profile, [])
    assert mand_score == 0.0
    assert opt_score == 0.0
    assert matched == []

    # Total match score should be modest
    res = MatchingEngine.evaluate_vacancy(profile, vac_no_tags)
    assert res.total_score <= 45
    assert any("не указаны теги" in w.lower() for w in res.warnings)


def test_one_out_of_ten_skills_low_score():
    profile = CandidateProfile(
        raw_text="",
        skills=["python"],
    )
    vac_many = VacancySummary(
        id=202,
        title="Fullstack Wizard",
        tags=[
            TagItem(name="python"),
            TagItem(name="react"),
            TagItem(name="vue"),
            TagItem(name="angular"),
            TagItem(name="c++"),
            TagItem(name="rust"),
            TagItem(name="kubernetes"),
            TagItem(name="terraform"),
            TagItem(name="aws"),
            TagItem(name="graphql"),
        ],
    )
    res = MatchingEngine.evaluate_vacancy(profile, vac_many)
    # 1 of 10 skills matched = 4 pts out of 40 for skills
    assert res.breakdown.mandatory_skills_score == 4.0
    assert "python" in res.matched_skills
    assert len(res.missing_required_skills) == 9
    assert res.total_score <= 50


def test_grade_scoring_hierarchy():
    score_exact, match_exact = ScoringModel.score_grade("junior", ["junior"])
    assert score_exact == 15.0
    assert match_exact == "exact"

    score_close, match_close = ScoringModel.score_grade("junior", ["middle"])
    assert score_close < 15.0
    assert match_close == "close"

    score_mis, match_mis = ScoringModel.score_grade("junior", ["senior"])
    assert score_mis <= 3.0
    assert match_mis == "mismatch"

    score_unk, match_unk = ScoringModel.score_grade("junior", [])
    assert match_unk == "unknown"


def test_specialization_scoring():
    profile = CandidateProfile(raw_text="", roles=["backend"])
    v_backend = VacancySummary(
        id=203,
        title="Backend Engineer",
        specializations=[SpecializationItem(code="backend_dev")],
    )
    score = ScoringModel.score_specialization(profile, v_backend)
    assert score == 20.0

    v_other = VacancySummary(
        id=204,
        title="Accountant",
        specializations=[SpecializationItem(code="accounting_tax_audit")],
    )
    score_low = ScoringModel.score_specialization(profile, v_other)
    assert score_low <= 5.0


def test_matching_engine_full_match():
    profile = CandidateProfile(
        raw_text="Junior Python developer",
        skills=["python", "fastapi", "postgresql", "docker"],
        roles=["backend"],
        grade="junior",
        work_formats=["remote"],
    )
    vac = VacancySummary(
        id=205,
        title="Junior Python Backend Developer",
        company_title="Acme Corp",
        work_format=["remote"],
        grades=[GradeItem(name="junior")],
        specializations=[SpecializationItem(code="backend_dev")],
        tags=[
            TagItem(name="python"),
            TagItem(name="fastapi"),
            TagItem(name="postgresql"),
            TagItem(name="docker"),
        ],
    )
    res = MatchingEngine.evaluate_vacancy(profile, vac)
    assert res.total_score >= 85
    assert res.eligibility in ("eligible", "needs_verification")
    assert res.grade_match == "exact"
    assert "python" in res.matched_skills
    assert "fastapi" in res.matched_skills
