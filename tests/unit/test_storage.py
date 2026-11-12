"""Unit tests for SQLite VacancyStorage."""

from pathlib import Path

from hirify_mcp.models import VacancySummary
from hirify_mcp.storage.sqlite import VacancyStorage


def test_sqlite_scenario_f_repeat_search(tmp_path: Path):
    """Scenario F: 1st search returns [1, 2, 3]; 2nd returns [2, 3, 4] -> 4 is new."""
    db_file = tmp_path / "test_history.db"
    storage = VacancyStorage(db_path=db_file)

    v1 = VacancySummary(id=1, title="Job 1", company_title="Co 1")
    v2 = VacancySummary(id=2, title="Job 2", company_title="Co 2")
    v3 = VacancySummary(id=3, title="Job 3", company_title="Co 3")
    v4 = VacancySummary(id=4, title="Job 4", company_title="Co 4")

    # 1. First search: [1, 2, 3]
    first_new = storage.record_vacancies([v1, v2, v3])
    assert set(first_new) == {1, 2, 3}

    # 2. Second search: [2, 3, 4]
    second_new = storage.record_vacancies([v2, v3, v4])
    assert second_new == [4]

    # Verify total vacancies stored is 4
    all_vacs = storage.list_vacancies()
    assert len(all_vacs) == 4


def test_user_status_preserved_on_repeated_search(tmp_path: Path):
    """User status (e.g. 'applied') must not be overwritten by repeated searches."""
    db_file = tmp_path / "test_history.db"
    storage = VacancyStorage(db_path=db_file)

    v1 = VacancySummary(id=10, title="Python Lead", company_title="TechCo")
    storage.record_vacancies([v1])

    # Candidate marks vacancy as 'applied' with notes
    storage.update_application_status(
        vacancy_id=10,
        status="applied",
        notes="Откликнулся через Greenhouse 12 ноября",
    )

    rec = storage.get_vacancy_record(10)
    assert rec is not None
    assert rec.application_status == "applied"
    assert rec.notes == "Откликнулся через Greenhouse 12 ноября"

    # Search runs again and discovers v1 again
    storage.record_vacancies([v1])

    # Status and notes must be intact!
    rec_after = storage.get_vacancy_record(10)
    assert rec_after is not None
    assert rec_after.application_status == "applied"
    assert rec_after.notes == "Откликнулся через Greenhouse 12 ноября"


def test_list_and_filter_saved(tmp_path: Path):
    db_file = tmp_path / "test_history.db"
    storage = VacancyStorage(db_path=db_file)

    v1 = VacancySummary(id=101, title="Job A")
    v2 = VacancySummary(id=102, title="Job B")
    storage.record_vacancies([v1, v2])

    storage.update_application_status(101, "saved")
    storage.update_application_status(102, "interview")

    saved_list = storage.list_vacancies(status="saved")
    assert len(saved_list) == 1
    assert saved_list[0].vacancy_id == 101

    interview_list = storage.list_vacancies(status="interview")
    assert len(interview_list) == 1
    assert interview_list[0].vacancy_id == 102


def test_clear_history(tmp_path: Path):
    db_file = tmp_path / "test_history.db"
    storage = VacancyStorage(db_path=db_file)
    v1 = VacancySummary(id=50, title="Job X")
    storage.record_vacancies([v1])
    assert len(storage.list_vacancies()) == 1

    count = storage.clear_history()
    assert count == 1
    assert len(storage.list_vacancies()) == 0
