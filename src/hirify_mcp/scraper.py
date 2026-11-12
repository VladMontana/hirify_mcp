"""Hirify API and HTML scraper using Scrapling Fetcher."""

from typing import Any, Dict, List, Optional
import logging
import urllib.parse
from scrapling.fetchers import Fetcher
from hirify_mcp.models import VacancyDetails, VacancySummary

logger = logging.getLogger(__name__)

HIRIFY_API_BASE = "https://api.hirify.me/api"


class HirifyScraper:
    """Scraper and client for Hirify job board using Scrapling."""

    def __init__(self, base_url: str = HIRIFY_API_BASE):
        self.base_url = base_url.rstrip("/")

    def search_vacancies(
        self,
        query: Optional[str] = None,
        grade: Optional[str] = None,
        work_format: Optional[str] = None,
        specialization: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> List[VacancySummary]:
        """Fetch list of vacancies matching query parameters.

        Args:
            query: Search keywords (e.g. 'python', 'fastapi', 'devops')
            grade: Seniority level ('intern', 'junior', 'middle', 'senior', 'lead')
            work_format: 'remote', 'hybrid', 'onsite'
            specialization: code (e.g. 'backend', 'frontend', 'devops', 'qa')
            page: 1-indexed starting page number
            limit: Maximum items to return
        """
        vacancies: List[VacancySummary] = []
        current_page = page
        max_pages = min(5, (limit + 14) // 15)  # Fetch at most needed pages, up to 5

        while len(vacancies) < limit and (current_page - page) < max_pages:
            param_list = [("page", str(current_page))]
            if query:
                param_list.append(("search", query))
            if grade:
                param_list.append(("grade[]", grade.lower()))
            if work_format:
                param_list.append(("work_format[]", work_format.lower()))
            if specialization:
                param_list.append(("specializations[]", specialization.lower()))

            query_str = urllib.parse.urlencode(param_list)
            url = f"{self.base_url}/vacancies?{query_str}"

            try:
                response = Fetcher.get(url)
                if response.status != 200:
                    logger.warning(f"Failed to fetch vacancies from Hirify. Status: {response.status}")
                    break

                data = response.json()
                raw_items = data.get("data", []) if isinstance(data, dict) else []
                if not raw_items:
                    break

                for item in raw_items:
                    try:
                        vac_model = VacancySummary.model_validate(item)
                        if vac_model.is_archived:
                            continue
                        vacancies.append(vac_model)
                        if len(vacancies) >= limit:
                            break
                    except Exception as ex:
                        logger.debug(f"Error parsing vacancy {item.get('id') if isinstance(item, dict) else item}: {ex}")
                        continue

                current_page += 1
            except Exception as e:
                logger.error(f"Error during Hirify fetch: {e}")
                break

        return vacancies[:limit]

    def get_vacancy_details(self, vacancy_id: int) -> Optional[VacancyDetails]:
        """Fetch complete vacancy data by its ID."""
        url = f"{self.base_url}/vacancies/{vacancy_id}"
        try:
            response = Fetcher.get(url)
            if response.status != 200:
                logger.warning(f"Failed to get vacancy {vacancy_id}. Status: {response.status}")
                return None
            data = response.json()
            return VacancyDetails.model_validate(data)
        except Exception as e:
            logger.error(f"Error getting vacancy details for {vacancy_id}: {e}")
            return None
