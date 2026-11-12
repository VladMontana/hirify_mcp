"""Backward-compatibility layer forwarding to HirifyClient."""

from typing import List, Optional

from hirify_mcp.clients.hirify import HirifyClient
from hirify_mcp.config import settings
from hirify_mcp.models import VacancyDetails, VacancySummary

HIRIFY_API_BASE = settings.API_BASE_URL


class HirifyScraper:
    """Backward-compatible wrapper around modern HirifyClient."""

    def __init__(self, base_url: str = HIRIFY_API_BASE):
        self.client = HirifyClient(base_url=base_url)
        self.base_url = self.client.base_url

    def search_vacancies(
        self,
        query: Optional[str] = None,
        grade: Optional[str] = None,
        work_format: Optional[str] = None,
        specialization: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> List[VacancySummary]:
        return self.client.search_vacancies(
            query=query,
            grade=grade,
            work_format=work_format,
            specialization=specialization,
            page=page,
            limit=limit,
        )

    def get_vacancy_details(self, vacancy_id: int) -> Optional[VacancyDetails]:
        return self.client.get_vacancy_details(vacancy_id=vacancy_id)
