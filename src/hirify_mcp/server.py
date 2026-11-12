"""MCP Server for Hirify vacancy search and profile matching."""

import json
from typing import Any, Dict, List, Optional
from mcp.server.mcpserver import MCPServer
from hirify_mcp.matcher import VacancyMatcher
from hirify_mcp.models import CandidateProfile
from hirify_mcp.parser import ResumeParser
from hirify_mcp.scraper import HirifyScraper

app = MCPServer("hirify-mcp")
scraper = HirifyScraper()


@app.tool()
def parse_profile(text: str) -> str:
    """Analyze a candidate's resume or free-form introductory text.

    Extracts technical skills, experience grade (junior/middle/senior/lead),
    roles, and preferred work formats.

    Args:
        text: Raw resume or introductory message from candidate
    """
    profile = ResumeParser.parse_profile(text)
    return profile.model_dump_json(indent=2)


@app.tool()
def search_vacancies(
    query: Optional[str] = None,
    grade: Optional[str] = None,
    work_format: Optional[str] = None,
    specialization: Optional[str] = None,
    limit: int = 15,
) -> str:
    """Search vacancies on Hirify using filters with stealth anti-bot bypass.

    Args:
        query: Search keywords (e.g. 'python', 'fastapi', 'devops')
        grade: Seniority level ('junior', 'middle', 'senior', 'lead')
        work_format: 'remote', 'hybrid', or 'onsite'
        specialization: Spec code (e.g. 'backend', 'frontend', 'qa', 'devops')
        limit: Max number of vacancies to return (default: 15)
    """
    vacancies = scraper.search_vacancies(
        query=query,
        grade=grade,
        work_format=work_format,
        specialization=specialization,
        limit=limit,
    )

    if not vacancies:
        return "По вашему запросу вакансий на Hirify не найдено."

    lines = [f"Найдено {len(vacancies)} вакансий на Hirify:\n"]
    for i, v in enumerate(vacancies, 1):
        tags_str = ", ".join(v.tag_names[:6]) if v.tag_names else "нет тегов"
        grades_str = ", ".join(v.grade_names) if v.grade_names else "любой"
        formats_str = ", ".join(v.work_format) if v.work_format else "не указан"

        salary_str = f" | **Зарплата:** {v.salary_display}" if v.salary_display else ""
        lines.append(
            f"### {i}. [{v.title}]({v.url})\n"
            f"- **Компания:** {v.company_title or 'Не указана'}\n"
            f"- **Грейд:** {grades_str} | **Формат:** {formats_str}{salary_str}\n"
            f"- **Теги стека:** {tags_str}\n"
            f"- **ID:** `{v.id}`\n"
        )

    return "\n".join(lines)


@app.tool()
def get_vacancy_details(vacancy_id: int) -> str:
    """Get full description and direct contact details for a specific vacancy.

    Args:
        vacancy_id: Unique Hirify vacancy ID
    """
    details = scraper.get_vacancy_details(vacancy_id)
    if not details:
        return f"Вакансия с ID {vacancy_id} не найдена или недоступна."

    contacts_info = []
    if details.apply_url:
        contacts_info.append(f"- Ссылка для отклика: {details.apply_url}")
    for c in details.contacts:
        if c.value:
            c_type = f" ({c.type})" if c.type else ""
            contacts_info.append(f"- Контакт{c_type}: {c.value}")

    contacts_block = "\n".join(contacts_info) if contacts_info else "Прямые контакты не указаны (смотрите ссылку на вакансию)"
    clean_desc = details.clear_text or details.text or "Описание отсутствует"

    # Truncate text if excessively long
    if len(clean_desc) > 3000:
        clean_desc = clean_desc[:3000] + "\n...[описание сокращено]..."

    salary_line = f"- **Зарплата:** {details.salary_display}\n" if details.salary_display else ""

    return (
        f"# {details.title}\n"
        f"**Компания:** {details.company_title or 'Не указана'}\n"
        f"**Ссылка на Hirify:** {details.url}\n\n"
        f"### Условия\n"
        f"- **Грейд:** {', '.join(details.grade_names) or 'Любой'}\n"
        f"- **Формат работы:** {', '.join(details.work_format) or 'Не указан'}\n"
        f"{salary_line}"
        f"- **Локация/Ограничения:** {details.remote_type or 'Не ограничено'}\n\n"
        f"### Контакты для отклика\n"
        f"{contacts_block}\n\n"
        f"### Описание\n"
        f"{clean_desc}\n"
    )


@app.tool()
def match_vacancies(
    profile_text: str,
    top_n: int = 10,
    work_format: Optional[str] = None,
    grade: Optional[str] = None,
    min_score: int = 40,
) -> str:
    """Main tool: matches candidate profile/resume to best fitting Hirify vacancies.

    Parses user skills and preferences, queries the Hirify platform using Scrapling,
    scores compatibility (0-100%), and returns a ranked list with explanations.

    Args:
        profile_text: Candidate's resume or free-form experience description
        top_n: Number of best-matching vacancies to return (default: 10)
        work_format: Override work format ('remote', 'hybrid', 'onsite') or leave None for auto-detect
        grade: Override grade ('junior', 'middle', 'senior', 'lead') or leave None for auto-detect
        min_score: Minimum match percentage threshold (default: 40)
    """
    # 1. Parse candidate profile
    profile = ResumeParser.parse_profile(profile_text)

    # Allow user override
    if work_format:
        profile.work_formats = [work_format.lower()]
    if grade:
        profile.grade = grade.lower()

    # 2. Build search queries & specialization
    primary_languages = {"python", "go", "golang", "javascript", "typescript", "rust", "java", "kotlin", "c++", "c#", "php", "ruby", "swift"}
    core_frameworks = {"react", "vue", "angular", "django", "fastapi", "spring", "flutter", "nodejs", "node"}

    role_to_spec = {
        "backend": "backend_dev",
        "frontend": "frontend_dev",
        "fullstack": "fullstack_dev",
        "devops": "devops",
        "qa": "qa",
        "mobile": "mobile_dev",
        "data": "data_engineering",
        "ml": "machine_learning",
        "ai": "ai_engineering",
    }
    effective_spec = None
    for r in profile.roles:
        if r in role_to_spec:
            effective_spec = role_to_spec[r]
            break

    selected_queries = []
    # 1. First priority: core frameworks (highest precision, e.g. fastapi, django, react)
    for s in profile.skills:
        if s in core_frameworks and s not in selected_queries:
            selected_queries.append(s)

    # 2. Second priority: programming languages
    for s in profile.skills:
        if s in primary_languages and s not in selected_queries:
            selected_queries.append(s)

    # 3. Third priority: specialized roles (qa, devops)
    for r in profile.roles:
        if r in {"qa", "devops"} and r not in selected_queries:
            selected_queries.insert(0, r)

    # 4. Remaining skills & roles
    for s in profile.skills:
        if s not in selected_queries:
            selected_queries.append(s)
    for r in profile.roles:
        if r not in selected_queries:
            selected_queries.append(r)

    # Pick up to 3 top queries for broader and more accurate coverage
    search_queries = selected_queries[:3]

    if not search_queries:
        search_queries = ["developer"]

    effective_format = profile.work_formats[0] if profile.work_formats else None
    effective_grade = profile.grade

    # 3. Fetch pool of vacancies via Scrapling
    gathered_vacancies = []
    seen_ids = set()

    for q in search_queries:
        vacs = scraper.search_vacancies(
            query=q,
            grade=effective_grade,
            work_format=effective_format,
            specialization=effective_spec,
            limit=25,
        )
        for v in vacs:
            if v.id not in seen_ids:
                seen_ids.add(v.id)
                gathered_vacancies.append(v)

    # Fallback search without specialization tag if too few gathered (Hirify often doesn't tag spec)
    if len(gathered_vacancies) < 15:
        for q in search_queries[:2]:
            fallback_vacs = scraper.search_vacancies(
                query=q,
                grade=effective_grade,
                work_format=effective_format,
                limit=25,
            )
            for v in fallback_vacs:
                if v.id not in seen_ids:
                    seen_ids.add(v.id)
                    gathered_vacancies.append(v)

    # Fallback search if grade filter was too strict
    if len(gathered_vacancies) < 10 and effective_grade:
        fallback_vacs = scraper.search_vacancies(
            query=search_queries[0],
            work_format=effective_format,
            limit=25,
        )
        for v in fallback_vacs:
            if v.id not in seen_ids:
                seen_ids.add(v.id)
                gathered_vacancies.append(v)

    if not gathered_vacancies:
        return (
            f"Не удалось найти вакансии по ключевым словам: {search_queries} "
            f"(грейд: {effective_grade or 'любой'}, формат: {effective_format or 'любой'})."
        )

    # 4. Rank and score vacancies
    matches = VacancyMatcher.match_many(
        profile=profile,
        vacancies=gathered_vacancies,
        min_score=min_score,
        top_n=top_n,
    )

    if not matches:
        return (
            f"Найдено {len(gathered_vacancies)} вакансий, но ни одна не набрала порог совместимости >= {min_score}%.\n"
            f"Попробуйте снизить `min_score` или расширить описание навыков."
        )

    # 5. Format human-friendly markdown response
    output_lines = [
        f"## 🎯 Топ-{len(matches)} подходящих вакансий на Hirify\n",
        f"**Распознанный профиль соискателя:**",
        f"- Стек: {', '.join(profile.skills) if profile.skills else 'не определен'}",
        f"- Грейд: {profile.grade or 'не указан'}",
        f"- Желаемый формат: {', '.join(profile.work_formats) if profile.work_formats else 'любой'}\n",
        "---\n",
    ]

    for idx, m in enumerate(matches, 1):
        contacts_str = ""
        if m.contacts:
            contacts_str = f"- **Откликнуться напрямую:** {', '.join(m.contacts[:2])}\n"
        salary_str = f"- **Зарплата:** {m.salary}\n" if m.salary else ""

        output_lines.append(
            f"### {idx}. [{m.title}]({m.url}) — **{m.total_score}% совпадение**\n"
            f"- **Компания:** {m.company}\n"
            f"{salary_str}"
            f"- **Анализ:** {m.summary}\n"
            f"- **Баллы:** Стек {m.breakdown.skill_score}/65, Грейд {m.breakdown.grade_score}/20, Формат {m.breakdown.format_score}/15\n"
            f"{contacts_str}"
        )

    return "\n".join(output_lines)


def main():
    """Entry point to run MCP server via stdio transport."""
    app.run()


if __name__ == "__main__":
    main()
