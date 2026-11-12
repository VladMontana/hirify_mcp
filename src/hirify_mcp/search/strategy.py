"""Smart search strategy for querying Hirify with query generation and fallback expansion."""

from typing import List, Optional, Set

from hirify_mcp.clients.hirify import HirifyClient
from hirify_mcp.config import logger
from hirify_mcp.models import CandidateProfile, VacancySummary
from hirify_mcp.parsing.normalizer import role_to_hirify_spec

CORE_FRAMEWORKS = {
    "fastapi",
    "django",
    "flask",
    "spring",
    "react",
    "vue",
    "angular",
    "next.js",
    "nuxt",
    "express",
    "nestjs",
    "flutter",
    "react native",
    "asp.net",
    "laravel",
    "symfony",
}

PRIMARY_LANGUAGES = {
    "python",
    "go",
    "golang",
    "typescript",
    "javascript",
    "rust",
    "java",
    "kotlin",
    "c++",
    "c#",
    ".net",
    "php",
    "ruby",
    "swift",
    "scala",
}


class SearchStrategy:
    """Orchestrates query generation, multi-stage API querying, and fallback expansion."""

    def __init__(self, client: Optional[HirifyClient] = None):
        self.client = client or HirifyClient()

    @classmethod
    def generate_search_queries(cls, profile: CandidateProfile) -> List[str]:
        """Generate a prioritized list of up to 4 distinct search queries."""
        queries: List[str] = []

        # 1. Frameworks first (highest precision)
        for skill in profile.skills:
            if skill in CORE_FRAMEWORKS and skill not in queries:
                queries.append(skill)

        # 2. Languages second
        for skill in profile.skills:
            if skill in PRIMARY_LANGUAGES and skill not in queries:
                queries.append(skill)

        # 3. Roles third
        for role in profile.roles:
            if role not in queries:
                queries.append(role)

        # 4. Remaining skills
        for skill in profile.skills:
            if skill not in queries:
                queries.append(skill)

        # Limit to top 3 queries to respect API request budget
        selected = queries[:3]
        if not selected:
            selected = ["developer"]

        return selected

    def execute_search(
        self,
        profile: CandidateProfile,
        max_vacancies: int = 40,
        fetch_details_top_n: int = 0,
    ) -> List[VacancySummary]:
        """Execute a balanced search using queries, fallbacks, and deduplication.

        Args:
            profile: Candidate profile
            max_vacancies: Maximum total unique vacancies to gather
            fetch_details_top_n: Fetch full vacancy details for top N items
        """
        search_queries = self.generate_search_queries(profile)
        effective_format = profile.work_formats[0] if profile.work_formats else None
        effective_grade = profile.grade

        effective_spec = None
        for r in profile.roles:
            spec = role_to_hirify_spec(r)
            if spec:
                effective_spec = spec
                break

        gathered: List[VacancySummary] = []
        seen_ids: Set[int] = set()

        # Phase 1: Targeted search with spec and filters
        for q in search_queries:
            try:
                vacs = self.client.search_vacancies(
                    query=q,
                    grade=effective_grade,
                    work_format=effective_format,
                    specialization=effective_spec,
                    limit=20,
                )
                for v in vacs:
                    if v.id not in seen_ids:
                        seen_ids.add(v.id)
                        gathered.append(v)
            except Exception as ex:
                logger.warning(
                    f"Error querying Hirify for '{q}' with spec '{effective_spec}': {ex}"
                )

        # Phase 2: Fallback without specialization (Hirify often doesn't tag specs)
        if len(gathered) < 15:
            logger.info(
                "Gathered < 15 vacancies, expanding search without specialization filter..."
            )
            for q in search_queries[:2]:
                try:
                    vacs = self.client.search_vacancies(
                        query=q,
                        grade=effective_grade,
                        work_format=effective_format,
                        limit=20,
                    )
                    for v in vacs:
                        if v.id not in seen_ids:
                            seen_ids.add(v.id)
                            gathered.append(v)
                except Exception as ex:
                    logger.warning(f"Error in fallback search for '{q}': {ex}")

        # Phase 3: Fallback without grade filter if still too few (apply grade filtering locally!)
        if len(gathered) < 10 and effective_grade:
            logger.info(
                "Gathered < 10 vacancies, querying without strict grade param for local filtering..."
            )
            try:
                vacs = self.client.search_vacancies(
                    query=search_queries[0],
                    work_format=effective_format,
                    limit=25,
                )
                for v in vacs:
                    if v.id not in seen_ids:
                        seen_ids.add(v.id)
                        gathered.append(v)
            except Exception as ex:
                logger.warning(f"Error in grade-less fallback search: {ex}")

        vacancies = gathered[:max_vacancies]

        # Stage 6.3: Optional two-stage detail fetching
        if fetch_details_top_n > 0 and vacancies:
            logger.info(f"Fetching full details for top {fetch_details_top_n} vacancies...")
            enriched_vacancies: List[VacancySummary] = []
            for i, v in enumerate(vacancies):
                if i < fetch_details_top_n:
                    try:
                        details = self.client.get_vacancy_details(v.id)
                        if details:
                            enriched_vacancies.append(details)
                            continue
                    except Exception as ex:
                        logger.warning(f"Failed to fetch details for vacancy {v.id}: {ex}")
                enriched_vacancies.append(v)
            vacancies = enriched_vacancies

        return vacancies
