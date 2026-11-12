"""Unit tests for HardFilter gating rules."""

from hirify_mcp.matching.filters import HardFilter
from hirify_mcp.models import CandidateProfile, GradeItem, SalaryItem, VacancySummary


def test_scenario_b_remote_only_vs_onsite():
    """Scenario B: Candidate requires remote only; vacancy is onsite only -> rejected."""
    profile = CandidateProfile(
        raw_text="",
        skills=["python"],
        work_formats=["remote"],
        remote_only=True,
    )
    vac_onsite = VacancySummary(
        id=101,
        title="Python Developer",
        work_format=["onsite"],
    )
    res = HardFilter.evaluate(profile, vac_onsite)
    assert res.is_eligible is False
    assert res.status == "ineligible"
    assert "work_format_mismatch" in res.failed_filters


def test_scenario_c_geography_ineligible():
    """Scenario C: Candidate in Russia; vacancy remote restricted to Germany -> ineligible."""
    profile = CandidateProfile(
        raw_text="",
        skills=["python"],
        work_formats=["remote"],
        current_country="russia",
        legal_work_countries=["russia"],
    )
    vac_germany = VacancySummary(
        id=102,
        title="Backend Engineer",
        work_format=["remote"],
        remote_restrictions=["germany"],
    )
    res = HardFilter.evaluate(profile, vac_germany)
    assert res.is_eligible is False
    assert res.status == "ineligible"
    assert "geography_mismatch" in res.failed_filters


def test_geography_needs_verification():
    """Vacancy remote without explicit geographic restrictions -> needs_verification."""
    profile = CandidateProfile(
        raw_text="",
        skills=["python"],
        work_formats=["remote"],
    )
    vac_unspecified = VacancySummary(
        id=103,
        title="Python Dev",
        work_format=["remote"],
        remote_restrictions=[],
        remote_type=None,
    )
    res = HardFilter.evaluate(profile, vac_unspecified)
    assert res.is_eligible is True
    assert res.status == "needs_verification"


def test_geography_global_eligible():
    profile = CandidateProfile(
        raw_text="",
        skills=["python"],
        work_formats=["remote"],
        current_country="russia",
    )
    vac_global = VacancySummary(
        id=104,
        title="Python Dev",
        work_format=["remote"],
        remote_type="global",
    )
    res = HardFilter.evaluate(profile, vac_global)
    assert res.is_eligible is True
    assert res.status == "eligible"


def test_scenario_a_junior_vs_senior():
    """Junior candidate vs Senior/Lead vacancy in strict mode -> rejected."""
    profile = CandidateProfile(
        raw_text="",
        skills=["python"],
        grade="junior",
    )
    vac_senior = VacancySummary(
        id=105,
        title="Lead Architect",
        grades=[GradeItem(name="senior"), GradeItem(name="lead")],
    )
    res = HardFilter.evaluate(profile, vac_senior, strict_mode=True)
    assert res.is_eligible is False
    assert "grade_mismatch" in res.failed_filters


def test_archived_vacancy_rejected():
    profile = CandidateProfile(raw_text="", skills=["python"])
    vac_archived = VacancySummary(
        id=106,
        title="Python Dev",
        is_archived=True,
    )
    res = HardFilter.evaluate(profile, vac_archived)
    assert res.is_eligible is False
    assert "archived" in res.failed_filters


def test_excluded_skills_rejected():
    profile = CandidateProfile(
        raw_text="",
        skills=["python"],
        excluded_skills=["php", "wordpress"],
    )
    vac_with_php = VacancySummary(
        id=107,
        title="PHP & Python Developer",
    )
    res = HardFilter.evaluate(profile, vac_with_php)
    assert res.is_eligible is False
    assert "exclusion_matched" in res.failed_filters


def test_salary_threshold_below_expectations():
    profile = CandidateProfile(
        raw_text="",
        skills=["python"],
        min_salary=4000.0,
        currency="USD",
    )
    vac_low_pay = VacancySummary(
        id=108,
        title="Python Dev",
        salary=SalaryItem(min=1500, max=2000, currency="USD", salary_period="month"),
    )
    res = HardFilter.evaluate(profile, vac_low_pay)
    assert res.is_eligible is False
    assert "salary_mismatch" in res.failed_filters
