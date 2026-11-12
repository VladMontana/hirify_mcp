"""Matching engine for scoring job vacancies against candidate profiles.

Calculates match scores based on:
1. Technical skills overlap (weight: 65%)
2. Seniority grade alignment (weight: 20%)
3. Work format compatibility (weight: 15%)

Generates human-readable feedback on why a vacancy matches and what skills are missing.
"""

from typing import List, Tuple
from hirify_mcp.models import (
    CandidateProfile,
    MatchBreakdown,
    MatchResult,
    VacancySummary,
)
from hirify_mcp.parser import CANONICAL_SKILL_MAP, ResumeParser

GRADE_HIERARCHY = {
    "intern": 0,
    "junior": 1,
    "middle": 2,
    "senior": 3,
    "lead": 4,
}


class VacancyMatcher:
    """Calculates compatibility score between candidate and vacancies."""

    @staticmethod
    def _extract_vacancy_skills(vacancy: VacancySummary) -> List[str]:
        """Extract canonical set of technical requirements/tags from vacancy tags and title."""
        skills = set()
        # Canonicalize explicit tags
        for t in vacancy.tag_names:
            skills.add(CANONICAL_SKILL_MAP.get(t.lower(), t.lower()))

        # Also extract skills safely from title using boundary-safe regex parser
        title_skills = ResumeParser.extract_skills(vacancy.title)
        for s in title_skills:
            skills.add(s)

        return sorted(list(skills))

    @classmethod
    def score_skills(cls, candidate_skills: List[str], vacancy_skills: List[str]) -> Tuple[float, List[str], List[str]]:
        """Calculate skill score out of 65 points."""
        c_set = {s.lower() for s in candidate_skills}
        v_set = {s.lower() for s in vacancy_skills}

        if not v_set:
            # If vacancy has no tags, give neutral base score
            return 35.0, [], []

        matched = sorted(list(c_set.intersection(v_set)))
        missing = sorted(list(v_set - c_set))

        # Percentage of vacancy requirements satisfied
        ratio = len(matched) / len(v_set)

        # Scale to max 65 points
        score = ratio * 65.0
        return score, matched, missing

    @classmethod
    def score_grade(cls, candidate_grade: str | None, vacancy_grades: List[str]) -> Tuple[float, str]:
        """Calculate grade alignment score out of 20 points."""
        if not candidate_grade or not vacancy_grades:
            # Neutral if neither specified
            return 14.0, "unknown"

        cand_level = GRADE_HIERARCHY.get(candidate_grade.lower(), 2)

        # Find closest grade in vacancy
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
    def score_format(cls, candidate_formats: List[str], vacancy_formats: List[str]) -> Tuple[float, bool]:
        """Calculate work format compatibility out of 15 points."""
        if not candidate_formats:
            # Candidate did not specify, assume any format is acceptable
            return 15.0, True

        c_fmts = {f.lower() for f in candidate_formats}
        v_fmts = {f.lower() for f in vacancy_formats}

        if not v_fmts:
            return 10.0, True

        overlap = c_fmts.intersection(v_fmts)
        if overlap:
            return 15.0, True
        else:
            # If candidate wants remote only, but vacancy is onsite only
            return 0.0, False

    @classmethod
    def match(cls, profile: CandidateProfile, vacancy: VacancySummary) -> MatchResult:
        """Score a single vacancy against candidate profile."""
        vacancy_skills = cls._extract_vacancy_skills(vacancy)
        skill_score, matched_skills, missing_skills = cls.score_skills(profile.skills, vacancy_skills)
        grade_score, grade_match = cls.score_grade(profile.grade, vacancy.grade_names)
        format_score, format_match = cls.score_format(profile.work_formats, vacancy.work_format)

        total = int(round(skill_score + grade_score + format_score))
        total = max(0, min(100, total))

        breakdown = MatchBreakdown(
            skill_score=round(skill_score, 1),
            grade_score=round(grade_score, 1),
            format_score=round(format_score, 1),
        )

        # Build human explanation
        reasons = []
        if matched_skills:
            reasons.append(f"Совпадение по стеку: {', '.join(matched_skills[:5])}")
        if missing_skills:
            reasons.append(f"Не указаны в резюме: {', '.join(missing_skills[:5])}")
        if grade_match == "exact":
            reasons.append("Грейд идеально совпадает")
        elif grade_match == "mismatch":
            reasons.append("Грейд отличается от желаемого")
        if not format_match:
            reasons.append(f"Формат работы {vacancy.work_format} не соответствует желаемому {profile.work_formats}")

        summary = " | ".join(reasons) if reasons else "Базовое соответствие профилю"

        # Direct contacts
        contacts_list = []
        if vacancy.apply_url:
            contacts_list.append(vacancy.apply_url)
        for c in vacancy.contacts:
            if c.value:
                contacts_list.append(c.value)

        return MatchResult(
            vacancy_id=vacancy.id,
            title=vacancy.title,
            company=vacancy.company_title or "Компания не указана",
            url=vacancy.url,
            total_score=total,
            breakdown=breakdown,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            grade_match=grade_match,
            format_match=format_match,
            summary=summary,
            contacts=contacts_list,
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
        """Rank and return top matching vacancies."""
        results = [cls.match(profile, v) for v in vacancies]
        filtered = [r for r in results if r.total_score >= min_score]
        filtered.sort(key=lambda r: r.total_score, reverse=True)
        return filtered[:top_n]
