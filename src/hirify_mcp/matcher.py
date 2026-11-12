"""Backward-compatible shim for VacancyMatcher preserving legacy API and scoring."""

from typing import List, Tuple

from hirify_mcp.matching.scoring import GRADE_HIERARCHY, ScoringModel
from hirify_mcp.models import (
    CandidateProfile,
    MatchBreakdown,
    MatchResult,
    VacancySummary,
)
from hirify_mcp.parsing.normalizer import CANONICAL_SKILL_MAP


class VacancyMatcher:
    """Backward-compatible wrapper preserving legacy VacancyMatcher API."""

    @staticmethod
    def _extract_vacancy_skills(vacancy: VacancySummary) -> List[str]:
        return ScoringModel.extract_vacancy_skills(vacancy)

    @classmethod
    def score_skills(
        cls, candidate_skills: List[str], vacancy_skills: List[str]
    ) -> Tuple[float, List[str], List[str]]:
        c_set = {CANONICAL_SKILL_MAP.get(s.lower(), s.lower()) for s in candidate_skills}
        v_set = {CANONICAL_SKILL_MAP.get(s.lower(), s.lower()) for s in vacancy_skills}

        if not v_set:
            return 35.0, [], []

        matched = sorted(list(c_set.intersection(v_set)))
        missing = sorted(list(v_set - c_set))

        ratio = len(matched) / len(v_set)
        score = ratio * 65.0
        return score, matched, missing

    @classmethod
    def score_grade(
        cls, candidate_grade: str | None, vacancy_grades: List[str]
    ) -> Tuple[float, str]:
        if not candidate_grade or not vacancy_grades:
            return 14.0, "unknown"

        cand_level = GRADE_HIERARCHY.get(candidate_grade.lower(), 2)

        best_diff = 999
        for vg in vacancy_grades:
            v_level = GRADE_HIERARCHY.get(vg.lower())
            if v_level is not None:
                diff = abs(cand_level - v_level)
                if diff < best_diff:
                    best_diff = diff

        if best_diff == 0:
            return 20.0, "exact"
        elif best_diff == 1:
            return 12.0, "close"
        else:
            return 4.0, "mismatch"

    @classmethod
    def score_format(
        cls, candidate_formats: List[str], vacancy_formats: List[str]
    ) -> Tuple[float, bool]:
        if not candidate_formats:
            return 15.0, True

        c_fmts = {f.lower() for f in candidate_formats}
        v_fmts = {f.lower() for f in vacancy_formats}

        if not v_fmts:
            return 10.0, True

        overlap = c_fmts.intersection(v_fmts)
        if overlap:
            return 15.0, True
        else:
            return 0.0, False

    @classmethod
    def match(cls, profile: CandidateProfile, vacancy: VacancySummary) -> MatchResult:
        vacancy_skills = cls._extract_vacancy_skills(vacancy)
        skill_score, matched_skills, missing_skills = cls.score_skills(
            profile.skills, vacancy_skills
        )
        grade_score, grade_match = cls.score_grade(profile.grade, vacancy.grade_names)
        format_score, format_match = cls.score_format(profile.work_formats, vacancy.work_format)

        total = int(round(skill_score + grade_score + format_score))
        total = max(0, min(100, total))

        breakdown = MatchBreakdown(
            mandatory_skills_score=round(skill_score * 40 / 65, 1),
            optional_skills_score=0.0,
            specialization_score=0.0,
            grade_score=round(grade_score * 15 / 20, 1),
            preferences_score=round(format_score * 10 / 15, 1),
        )

        return MatchResult(
            vacancy_id=vacancy.id,
            title=vacancy.title,
            company=vacancy.company_title or "Компания не указана",
            url=vacancy.url,
            total_score=total,
            breakdown=breakdown,
            matched_skills=matched_skills,
            missing_required_skills=missing_skills,
            missing_optional_skills=[],
            grade_match=grade_match,
            format_match=format_match,
            summary="Базовое соответствие профилю",
            explanation=f"Стек {skill_score}/65, Грейд {grade_score}/20, Формат {format_score}/15",
            contacts=vacancy.direct_links,
            salary=vacancy.salary_display,
        )

    @classmethod
    def match_many(
        cls,
        profile: CandidateProfile,
        vacancies: List[VacancySummary],
        min_score: int = 40,
        top_n: int = 10,
    ) -> List[MatchResult]:
        results = [cls.match(profile, v) for v in vacancies]
        filtered = [r for r in results if r.total_score >= min_score]
        filtered.sort(key=lambda r: r.total_score, reverse=True)
        return filtered[:top_n]


__all__ = ["GRADE_HIERARCHY", "VacancyMatcher"]
