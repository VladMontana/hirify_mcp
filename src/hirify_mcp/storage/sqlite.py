"""SQLite storage for tracking vacancies, application statuses, and search history."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from hirify_mcp.config import settings
from hirify_mcp.models import (
    ApplicationStatus,
    MatchResult,
    SavedVacancyRecord,
    VacancySummary,
)


class VacancyStorage:
    """Thread-safe SQLite storage for candidate job search history."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.get_db_path()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database schema if not already present."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS vacancies (
                    vacancy_id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT,
                    url TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    last_checked_at TEXT NOT NULL,
                    salary TEXT,
                    work_format TEXT,
                    remote_type TEXT,
                    raw_data_json TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS applications (
                    vacancy_id INTEGER PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'new',
                    notes TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (vacancy_id) REFERENCES vacancies(vacancy_id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_vacancies_last_checked
                ON vacancies (last_checked_at DESC)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_applications_status
                ON applications (status)
                """
            )
            conn.commit()

    def record_vacancies(
        self,
        vacancies: List[VacancySummary],
        matches: Optional[List[MatchResult]] = None,
    ) -> List[int]:
        """Save discovered vacancies to SQLite.

        Returns:
            List of newly discovered vacancy IDs (not seen previously).
        """
        now = datetime.now(timezone.utc).isoformat()
        new_ids: List[int] = []

        {m.vacancy_id: m.total_score for m in (matches or [])}

        with self._get_connection() as conn:
            cursor = conn.cursor()
            for v in vacancies:
                cursor.execute(
                    "SELECT vacancy_id FROM vacancies WHERE vacancy_id = ?",
                    (v.id,),
                )
                existing = cursor.fetchone()

                formats_str = ", ".join(v.work_format) if v.work_format else None
                salary_str = v.salary_display

                if existing is None:
                    # Brand new vacancy
                    new_ids.append(v.id)
                    cursor.execute(
                        """
                        INSERT INTO vacancies (
                            vacancy_id, title, company, url, detected_at, last_checked_at,
                            salary, work_format, remote_type, raw_data_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            v.id,
                            v.title,
                            v.company_title or "Не указана",
                            v.url,
                            now,
                            now,
                            salary_str,
                            formats_str,
                            v.remote_type,
                            v.model_dump_json(),
                        ),
                    )
                    # Insert initial 'new' status
                    cursor.execute(
                        """
                        INSERT INTO applications (vacancy_id, status, notes, updated_at)
                        VALUES (?, 'new', NULL, ?)
                        """,
                        (v.id, now),
                    )
                else:
                    # Update last checked timestamp, without touching user application status
                    cursor.execute(
                        """
                        UPDATE vacancies
                        SET last_checked_at = ?,
                            salary = COALESCE(?, salary),
                            work_format = COALESCE(?, work_format),
                            remote_type = COALESCE(?, remote_type)
                        WHERE vacancy_id = ?
                        """,
                        (now, salary_str, formats_str, v.remote_type, v.id),
                    )

            conn.commit()

        return new_ids

    def update_application_status(
        self,
        vacancy_id: int,
        status: ApplicationStatus,
        notes: Optional[str] = None,
    ) -> bool:
        """Update candidate interaction status for a vacancy (e.g. applied, interview)."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Ensure vacancy row exists to satisfy foreign key
            cursor.execute(
                """
                INSERT OR IGNORE INTO vacancies (
                    vacancy_id, title, company, url, detected_at, last_checked_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    vacancy_id,
                    f"Вакансия {vacancy_id}",
                    "Не указана",
                    f"https://hirify.me/jobs/{vacancy_id}",
                    now,
                    now,
                ),
            )
            cursor.execute(
                """
                INSERT INTO applications (vacancy_id, status, notes, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(vacancy_id) DO UPDATE SET
                    status = excluded.status,
                    notes = COALESCE(excluded.notes, applications.notes),
                    updated_at = excluded.updated_at
                """,
                (vacancy_id, status, notes, now),
            )
            conn.commit()
            return cursor.rowcount > 0

    def list_vacancies(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[SavedVacancyRecord]:
        """List tracked vacancies, optionally filtered by application status."""
        records: List[SavedVacancyRecord] = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT
                    v.vacancy_id, v.title, v.company, v.url, v.detected_at, v.last_checked_at,
                    a.status, a.notes, v.salary, v.work_format, v.remote_type
                FROM vacancies v
                LEFT JOIN applications a ON v.vacancy_id = a.vacancy_id
            """
            params: list = []
            if status:
                query += " WHERE a.status = ?"
                params.append(status)

            query += " ORDER BY v.last_checked_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            for row in cursor.fetchall():
                records.append(
                    SavedVacancyRecord(
                        vacancy_id=row["vacancy_id"],
                        title=row["title"],
                        company=row["company"],
                        url=row["url"],
                        detected_at=row["detected_at"],
                        last_checked_at=row["last_checked_at"],
                        application_status=row["status"] or "new",
                        notes=row["notes"],
                        salary=row["salary"],
                        work_format=row["work_format"],
                        remote_type=row["remote_type"],
                    )
                )
        return records

    def get_new_vacancies(self, limit: int = 20) -> List[SavedVacancyRecord]:
        """Fetch recently discovered vacancies with 'new' status."""
        return self.list_vacancies(status="new", limit=limit)

    def get_vacancy_record(self, vacancy_id: int) -> Optional[SavedVacancyRecord]:
        """Get tracking record for a single vacancy."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    v.vacancy_id, v.title, v.company, v.url, v.detected_at, v.last_checked_at,
                    a.status, a.notes, v.salary, v.work_format, v.remote_type
                FROM vacancies v
                LEFT JOIN applications a ON v.vacancy_id = a.vacancy_id
                WHERE v.vacancy_id = ?
                """,
                (vacancy_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return SavedVacancyRecord(
                vacancy_id=row["vacancy_id"],
                title=row["title"],
                company=row["company"],
                url=row["url"],
                detected_at=row["detected_at"],
                last_checked_at=row["last_checked_at"],
                application_status=row["status"] or "new",
                notes=row["notes"],
                salary=row["salary"],
                work_format=row["work_format"],
                remote_type=row["remote_type"],
            )

    def clear_history(self) -> int:
        """Clear all stored vacancy history. Returns number of removed vacancies."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM vacancies")
            count = int(cursor.fetchone()[0])
            cursor.execute("DELETE FROM applications")
            cursor.execute("DELETE FROM vacancies")
            conn.commit()
            return count
