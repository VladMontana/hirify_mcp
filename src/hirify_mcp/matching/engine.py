"""Matching engine combining hard gating filters and weighted scoring."""

from typing import Dict, List

from hirify_mcp.matching.filters import HardFilter
from hirify_mcp.matching.scoring import ScoringModel
from hirify_mcp.models import (
    CandidateProfile,
    MatchBreakdown,
    MatchResult,
    MatchSummaryResponse,
    VacancySummary,
)


class MatchingEngine:
    """Core matching engine for evaluating vacancies against candidate profiles."""

    @classmethod
    def evaluate_vacancy(
        cls,
        profile: CandidateProfile,
        vacancy: VacancySummary,
        strict_mode: bool = True,
        strict_salary: bool = False,
    ) -> MatchResult:
        """Evaluate a single vacancy through hard filters and scoring."""
        # 1. Hard filters gating
        filter_res = HardFilter.evaluate(
            profile=profile,
            vacancy=vacancy,
            strict_mode=strict_mode,
            strict_salary=strict_salary,
        )

        vac_skills = ScoringModel.extract_vacancy_skills(vacancy)
        direct_contacts = vacancy.direct_links

        if not filter_res.is_eligible:
            # Vacancy failed hard filters - return 0 score with explicit exclusion reasons
            reasons_text = "; ".join(filter_res.reasons)
            return MatchResult(
                vacancy_id=vacancy.id,
                title=vacancy.title,
                company=vacancy.company_title or "Компания не указана",
                url=vacancy.url,
                total_score=0,
                eligibility="ineligible",
                breakdown=MatchBreakdown(),
                matched_skills=[],
                missing_required_skills=vac_skills,
                missing_optional_skills=[],
                grade_match="mismatch",
                format_match=False,
                remote_eligibility=filter_res.status,
                salary=vacancy.salary_display,
                contacts=direct_contacts,
                warnings=filter_res.reasons,
                summary=f"Исключена обязательным фильтром: {reasons_text}",
                explanation=f"Вакансия не прошла проверку обязательных условий: {reasons_text}.",
            )

        # 2. Score eligible vacancy
        breakdown, matched_skills, missing_req, missing_opt, grade_match, format_match = (
            ScoringModel.calculate_breakdown(profile, vacancy, vac_skills)
        )

        raw_total = (
            breakdown.mandatory_skills_score
            + breakdown.optional_skills_score
            + breakdown.specialization_score
            + breakdown.grade_score
            + breakdown.preferences_score
        )
        total_score = max(0, min(100, int(round(raw_total))))

        # 3. Assemble human explanation and warnings
        strengths: List[str] = []
        gaps: List[str] = []
        warnings: List[str] = []

        if matched_skills:
            strengths.append(
                f"Стек: совпало {len(matched_skills)} навыков ({', '.join(matched_skills[:5])})"
            )
        else:
            if not vac_skills:
                warnings.append("В вакансии не указаны теги технологий; скоринг по стеку снижен")
            else:
                gaps.append("Нет прямого совпадения по ключевым технологиям")

        if missing_req:
            gaps.append(f"Не указаны в резюме: {', '.join(missing_req[:4])}")

        if grade_match == "exact":
            strengths.append("Грейд точно соответствует")
        elif grade_match == "close":
            strengths.append("Грейд близкий к желаемому")
        elif grade_match == "mismatch":
            gaps.append("Грейд отличается от целевого")

        if not format_match:
            warnings.append(f"Формат {vacancy.work_format} не совпадает с предпочтениями")

        if filter_res.status == "needs_verification":
            warnings.append("Географические ограничения удаленки требуют уточнения у работодателя")

        if not vacancy.salary and profile.min_salary:
            warnings.append("Уровень зарплаты в вакансии не указан")

        summary_parts = strengths if strengths else ["Базовое совпадение профиля"]
        summary = " | ".join(summary_parts)

        expl_parts = []
        if strengths:
            expl_parts.append(f"Плюсы: {'; '.join(strengths)}.")
        if gaps:
            expl_parts.append(f"Недостающие навыки: {'; '.join(gaps)}.")
        if warnings:
            expl_parts.append(f"Внимание: {'; '.join(warnings)}.")
        explanation = " ".join(expl_parts)

        return MatchResult(
            vacancy_id=vacancy.id,
            title=vacancy.title,
            company=vacancy.company_title or "Компания не указана",
            url=vacancy.url,
            total_score=total_score,
            eligibility=filter_res.status,
            breakdown=breakdown,
            matched_skills=matched_skills,
            missing_required_skills=missing_req,
            missing_optional_skills=missing_opt,
            grade_match=grade_match,
            format_match=format_match,
            remote_eligibility=filter_res.status,
            salary=vacancy.salary_display,
            contacts=direct_contacts,
            warnings=warnings,
            summary=summary,
            explanation=explanation,
        )

    @classmethod
    def match_many(
        cls,
        profile: CandidateProfile,
        vacancies: List[VacancySummary],
        min_score: int = 40,
        top_n: int = 10,
        strict_mode: bool = True,
        strict_salary: bool = False,
    ) -> MatchSummaryResponse:
        """Filter, score, and rank vacancies, returning structured results."""
        evaluated: List[MatchResult] = []
        excluded_count = 0
        exclusion_reasons: Dict[str, int] = {}

        for v in vacancies:
            res = cls.evaluate_vacancy(
                profile=profile,
                vacancy=v,
                strict_mode=strict_mode,
                strict_salary=strict_salary,
            )
            if res.eligibility == "ineligible":
                excluded_count += 1
                for w in res.warnings:
                    exclusion_reasons[w] = exclusion_reasons.get(w, 0) + 1
            else:
                evaluated.append(res)

        # Filter by minimum score
        passing = [r for r in evaluated if r.total_score >= min_score]

        # Tie-breaker sorting:
        # 1. Total score desc
        # 2. Confirmed remote eligibility ("eligible" > "needs_verification")
        # 3. Number of matched skills desc
        def sort_key(r: MatchResult):
            remote_rank = 1 if r.remote_eligibility == "eligible" else 0
            return (r.total_score, remote_rank, len(r.matched_skills))

        passing.sort(key=sort_key, reverse=True)
        top_matches = passing[:top_n]

        return MatchSummaryResponse(
            total_gathered=len(vacancies),
            total_eligible=len(evaluated),
            total_excluded=excluded_count,
            exclusion_reasons=exclusion_reasons,
            matches=top_matches,
            profile=profile,
        )
