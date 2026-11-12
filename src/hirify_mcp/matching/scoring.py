"""Scoring model and weight calculations for vacancy matching."""

from typing import List, Optional, Set, Tuple

from hirify_mcp.models import CandidateProfile, MatchBreakdown, VacancySummary
from hirify_mcp.parsing.normalizer import normalize_skill, role_to_hirify_spec
from hirify_mcp.parsing.resume import ResumeParser

GRADE_HIERARCHY = {
    "trainee": 0,
    "intern": 0,
    "junior": 1,
    "middle": 2,
    "senior": 3,
    "lead": 4,
    "head": 5,
    "director": 6,
    "c_level": 7,
}


class ScoringModel:
    """Configurable scoring engine calculating candidate-vacancy compatibility (0-100)."""

    WEIGHT_MANDATORY_SKILLS: float = 40.0
    WEIGHT_OPTIONAL_SKILLS: float = 15.0
    WEIGHT_SPECIALIZATION: float = 20.0
    WEIGHT_GRADE: float = 15.0
    WEIGHT_PREFERENCES: float = 10.0

    @classmethod
    def extract_vacancy_skills(cls, vacancy: VacancySummary) -> List[str]:
        """Extract canonical technical requirements from vacancy tags and title."""
        skills: Set[str] = set()

        for t in vacancy.tag_names:
            skills.add(normalize_skill(t))

        # Safely extract skills from vacancy title
        title_skills = ResumeParser.extract_skills(vacancy.title)
        for s in title_skills:
            skills.add(normalize_skill(s))

        return sorted(list(skills))

    @classmethod
    def score_skills(
        cls,
        profile: CandidateProfile,
        vacancy_skills: List[str],
    ) -> Tuple[float, float, List[str], List[str], List[str]]:
        """Calculate mandatory skills score (0-40) and optional skills score (0-15).

        Returns:
            Tuple[mandatory_score, optional_score, matched_skills, missing_required, missing_optional]
        """
        if not vacancy_skills:
            # If vacancy has no technical tags or requirements, DO NOT award full points!
            return 0.0, 0.0, [], [], []

        cand_primary = {normalize_skill(s) for s in profile.skills}
        cand_additional = {normalize_skill(s) for s in profile.additional_skills}
        cand_all = cand_primary.union(cand_additional)

        vac_set = {normalize_skill(s) for s in vacancy_skills}

        matched = sorted(list(cand_all.intersection(vac_set)))
        missing = sorted(list(vac_set - cand_all))

        # Separate missing into required vs optional if candidate has required_skills
        if profile.required_skills:
            missing_required = [s for s in missing if s in profile.required_skills]
            missing_optional = [s for s in missing if s not in profile.required_skills]
        else:
            missing_required = missing
            missing_optional = []

        ratio = len(matched) / len(vac_set)
        mandatory_score = round(ratio * cls.WEIGHT_MANDATORY_SKILLS, 1)

        # Bonus for additional technologies if matched
        additional_matches = cand_additional.intersection(vac_set)
        optional_ratio = (
            len(additional_matches) / max(1, len(cand_additional))
            if cand_additional
            else (0.5 if matched else 0.0)
        )
        optional_score = round(optional_ratio * cls.WEIGHT_OPTIONAL_SKILLS, 1)

        return mandatory_score, optional_score, matched, missing_required, missing_optional

    @classmethod
    def score_specialization(
        cls,
        profile: CandidateProfile,
        vacancy: VacancySummary,
    ) -> float:
        """Calculate role and domain specialization alignment (0-20 points)."""
        if not profile.roles:
            return 10.0  # Neutral if candidate has no specific role

        cand_specs = {role_to_hirify_spec(r) for r in profile.roles if role_to_hirify_spec(r)}
        vac_specs = set(vacancy.specialization_codes)

        # 1. Exact spec code match
        if cand_specs.intersection(vac_specs):
            return cls.WEIGHT_SPECIALIZATION

        # 2. Check title keywords for candidate roles
        title_lower = vacancy.title.lower()
        for r in profile.roles:
            if r.lower() in title_lower:
                return cls.WEIGHT_SPECIALIZATION * 0.85

        # 3. Partial overlap or related disciplines (e.g. backend / fullstack)
        if "backend_dev" in cand_specs and "fullstack_dev" in vac_specs:
            return cls.WEIGHT_SPECIALIZATION * 0.7
        if "fullstack_dev" in cand_specs and (
            "backend_dev" in vac_specs or "frontend_dev" in vac_specs
        ):
            return cls.WEIGHT_SPECIALIZATION * 0.7

        return 4.0

    @classmethod
    def score_grade(
        cls,
        candidate_grade: Optional[str],
        vacancy_grades: List[str],
    ) -> Tuple[float, str]:
        """Calculate seniority level alignment (0-15 points).

        Returns:
            Tuple[score, grade_match_type ("exact", "close", "mismatch", "unknown")]
        """
        if not candidate_grade or not vacancy_grades:
            return round(cls.WEIGHT_GRADE * 0.5, 1), "unknown"

        cand_level = GRADE_HIERARCHY.get(candidate_grade.lower(), 2)

        best_diff = 999
        for vg in vacancy_grades:
            v_level = GRADE_HIERARCHY.get(vg.lower())
            if v_level is not None:
                diff = abs(cand_level - v_level)
                if diff < best_diff:
                    best_diff = diff

        if best_diff == 0:
            return cls.WEIGHT_GRADE, "exact"
        elif best_diff == 1:
            return round(cls.WEIGHT_GRADE * 0.65, 1), "close"
        else:
            return round(cls.WEIGHT_GRADE * 0.15, 1), "mismatch"

    @classmethod
    def score_preferences(
        cls,
        profile: CandidateProfile,
        vacancy: VacancySummary,
    ) -> Tuple[float, bool]:
        """Calculate preference fulfillment (0-10 points: 5 format + 5 salary)."""
        score = 0.0

        # Work format match (5 pts)
        format_match = True
        if profile.work_formats:
            c_fmts = {f.lower() for f in profile.work_formats}
            v_fmts = {f.lower() for f in vacancy.work_format}
            if not v_fmts:
                score += 3.0
            elif c_fmts.intersection(v_fmts):
                score += 5.0
            else:
                format_match = False
        else:
            score += 4.0

        # Salary match (5 pts)
        if vacancy.salary:
            score += 5.0
        else:
            score += 2.5  # Neutral for missing salary

        return round(score, 1), format_match

    @classmethod
    def calculate_breakdown(
        cls,
        profile: CandidateProfile,
        vacancy: VacancySummary,
        vacancy_skills: List[str],
    ) -> Tuple[MatchBreakdown, List[str], List[str], List[str], str, bool]:
        """Calculate all scoring sub-components."""
        mand_score, opt_score, matched_skills, missing_req, missing_opt = cls.score_skills(
            profile, vacancy_skills
        )
        spec_score = cls.score_specialization(profile, vacancy)
        grade_score, grade_match = cls.score_grade(profile.grade, vacancy.grade_names)
        pref_score, format_match = cls.score_preferences(profile, vacancy)

        breakdown = MatchBreakdown(
            mandatory_skills_score=mand_score,
            optional_skills_score=opt_score,
            specialization_score=spec_score,
            grade_score=grade_score,
            preferences_score=pref_score,
        )

        return breakdown, matched_skills, missing_req, missing_opt, grade_match, format_match
