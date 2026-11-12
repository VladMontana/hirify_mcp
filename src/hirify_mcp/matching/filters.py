"""Hard filtering module for gating job vacancies before scoring."""

from typing import Any, Dict, List, Optional

from hirify_mcp.models import CandidateProfile, EligibilityStatus, HardFilterResult, VacancySummary

# Basic currency approximations against USD for sanity checks
CURRENCY_TO_USD = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.28,
    "RUB": 0.011,
    "KZT": 0.002,
    "CAD": 0.74,
}


class HardFilter:
    """Evaluates strict suitability criteria for a vacancy before scoring."""

    @classmethod
    def check_work_format(
        cls,
        profile: CandidateProfile,
        vacancy: VacancySummary,
    ) -> Optional[str]:
        """Check if vacancy work format conflicts with candidate preferences."""
        if profile.remote_only or (
            profile.work_formats
            and "remote" in profile.work_formats
            and len(profile.work_formats) == 1
        ):
            if not vacancy.work_format:
                return "Формат работы в вакансии не указан (требуется подтвержденная удаленка)"
            vac_formats = [f.lower() for f in vacancy.work_format]
            if "remote" not in vac_formats:
                return f"Вакансия только для {', '.join(vac_formats)}, соискатель требует только remote"
        return None

    @classmethod
    def check_geography(
        cls,
        profile: CandidateProfile,
        vacancy: VacancySummary,
    ) -> tuple[EligibilityStatus, Optional[str]]:
        """Verify geographic restrictions for remote work."""
        vac_formats = [f.lower() for f in vacancy.work_format]
        if "remote" not in vac_formats:
            # Not a remote position
            return "eligible", None

        # Check explicit restrictions
        candidate_countries = set()
        if profile.current_country:
            candidate_countries.add(profile.current_country.lower())
        for c in profile.legal_work_countries:
            candidate_countries.add(c.lower())

        vac_restrictions = [r.lower() for r in vacancy.remote_restrictions]
        allowed_locs = [a.lower() for a in vacancy.allowed_locations]
        ineligible_locs = [i.lower() for i in vacancy.ineligible_countries]

        # 1. Candidate is in explicit ineligible list
        if candidate_countries and any(c in ineligible_locs for c in candidate_countries):
            return "ineligible", f"Страна соискателя входит в список исключенных: {ineligible_locs}"

        # 2. Vacancy specifies restricted countries (e.g. united_states, germany, russia)
        required_regions = vac_restrictions or allowed_locs
        if required_regions:
            if not candidate_countries:
                return (
                    "needs_verification",
                    f"Вакансия ограничена регионами {required_regions}, локация соискателя не указана",
                )

            # Check overlap
            overlap = candidate_countries.intersection(set(required_regions))
            if not overlap:
                # Also check remote_type e.g. "usa", "europe", "russia"
                remote_type = (vacancy.remote_type or "").lower()
                if remote_type and remote_type in candidate_countries:
                    return "eligible", None
                return (
                    "ineligible",
                    f"Удаленка разрешена только из {required_regions}, соискатель: {list(candidate_countries)}",
                )

        # 3. Vacancy has remote_type == 'global'
        if (vacancy.remote_type or "").lower() in ("global", "worldwide"):
            return "eligible", None

        # 4. If remote restrictions are completely unspecified
        if not required_regions and not vacancy.remote_type:
            return (
                "needs_verification",
                "Географические ограничения удаленки в вакансии не указаны явно",
            )

        return "eligible", None

    @classmethod
    def check_grade(
        cls,
        profile: CandidateProfile,
        vacancy: VacancySummary,
        strict_mode: bool = True,
    ) -> Optional[str]:
        """Check if seniority level is compatible."""
        if not profile.grade:
            return None

        cand_grade = profile.grade.lower()
        vac_grades = [g.lower() for g in vacancy.grade_names]
        if not vac_grades:
            return None  # Unknown vacancy grade passes with warning

        if cand_grade in ("trainee", "junior"):
            # Junior / Trainee should NOT be matched with Senior / Lead in strict mode
            senior_grades = {"senior", "lead", "head", "director", "c_level"}
            if any(g in senior_grades for g in vac_grades) and not any(
                g in ("trainee", "junior") for g in vac_grades
            ):
                return f"Вакансия уровня {vac_grades}, кандидат — {cand_grade}"

        elif cand_grade in ("senior", "lead"):
            if strict_mode:
                entry_grades = {"trainee", "intern"}
                if any(g in entry_grades for g in vac_grades) and not any(
                    g in ("senior", "lead", "middle") for g in vac_grades
                ):
                    return f"Вакансия начального уровня {vac_grades}, кандидат — {cand_grade}"

        return None

    @classmethod
    def check_salary(
        cls,
        profile: CandidateProfile,
        vacancy: VacancySummary,
        strict_salary: bool = False,
    ) -> Optional[str]:
        """Check salary threshold if candidate has specific minimum requirements."""
        if not profile.min_salary or not vacancy.salary:
            if strict_salary and profile.min_salary and not vacancy.salary:
                return (
                    "Зарплата в вакансии не указана, соискатель требует только вакансии с зарплатой"
                )
            return None

        # Compare if currencies match or are convertible
        vac_curr = (vacancy.salary.currency or "").upper()
        cand_curr = (profile.currency or "USD").upper()
        vac_max = vacancy.salary.max or vacancy.salary.min

        if vac_max is None:
            return None

        # Convert to USD for comparison
        vac_rate = CURRENCY_TO_USD.get(vac_curr)
        cand_rate = CURRENCY_TO_USD.get(cand_curr)

        if vac_rate and cand_rate:
            vac_usd = vac_max * vac_rate
            cand_usd = profile.min_salary * cand_rate
            # Check period adjustment: if vacancy is hourly, convert to monthly (~160 hours)
            if vacancy.salary.salary_period == "hour":
                vac_usd *= 160
            elif vacancy.salary.salary_period == "year":
                vac_usd /= 12

            cand_period = profile.salary_period or "month"
            if cand_period == "year":
                cand_usd /= 12
            elif cand_period == "hour":
                cand_usd *= 160

            # Allow 10% buffer
            if vac_usd < (cand_usd * 0.9):
                return f"Максимальная зарплата вакансии ({vacancy.salary_display}) ниже ожиданий соискателя ({int(profile.min_salary)} {cand_curr})"
        elif vac_curr == cand_curr:
            if vac_max < profile.min_salary:
                return f"Зарплата ({vacancy.salary_display}) ниже ожиданий ({int(profile.min_salary)} {cand_curr})"

        return None

    @classmethod
    def check_exclusions(
        cls,
        profile: CandidateProfile,
        vacancy: VacancySummary,
    ) -> Optional[str]:
        """Check for excluded skills or roles."""
        title_lower = vacancy.title.lower()
        tags_lower = set(vacancy.tag_names)

        # Excluded skills
        for exc_s in profile.excluded_skills:
            exc = exc_s.lower()
            if exc in tags_lower or exc in title_lower:
                return f"Вакансия содержит исключенную технологию: {exc}"

        # Excluded roles
        for exc_r in profile.excluded_roles:
            exc_role = exc_r.lower()
            if exc_role in title_lower:
                return f"Вакансия содержит исключенную должность: {exc_role}"

        return None

    @classmethod
    def evaluate(
        cls,
        profile: CandidateProfile,
        vacancy: VacancySummary,
        strict_mode: bool = True,
        strict_salary: bool = False,
    ) -> HardFilterResult:
        """Run all hard gating filters against the vacancy."""
        reasons: List[str] = []
        failed_filters: List[str] = []
        details: Dict[str, Any] = {}

        # 1. Archived check
        if vacancy.is_archived:
            return HardFilterResult(
                is_eligible=False,
                status="ineligible",
                reasons=["Вакансия находится в архиве"],
                failed_filters=["archived"],
            )

        # 2. Work format check
        fmt_error = cls.check_work_format(profile, vacancy)
        if fmt_error:
            reasons.append(fmt_error)
            failed_filters.append("work_format_mismatch")

        # 3. Geography check
        geo_status, geo_reason = cls.check_geography(profile, vacancy)
        details["remote_eligibility"] = geo_status
        if geo_status == "ineligible":
            reasons.append(geo_reason or "Географическое несоответствие")
            failed_filters.append("geography_mismatch")
        elif geo_reason:
            details["geo_warning"] = geo_reason

        # 4. Grade check
        grade_error = cls.check_grade(profile, vacancy, strict_mode=strict_mode)
        if grade_error:
            reasons.append(grade_error)
            failed_filters.append("grade_mismatch")

        # 5. Salary check
        salary_error = cls.check_salary(profile, vacancy, strict_salary=strict_salary)
        if salary_error:
            reasons.append(salary_error)
            failed_filters.append("salary_mismatch")

        # 6. Exclusions check
        excl_error = cls.check_exclusions(profile, vacancy)
        if excl_error:
            reasons.append(excl_error)
            failed_filters.append("exclusion_matched")

        is_eligible = len(failed_filters) == 0
        overall_status: EligibilityStatus = "eligible" if is_eligible else "ineligible"
        if is_eligible and geo_status == "needs_verification":
            overall_status = "needs_verification"

        return HardFilterResult(
            is_eligible=is_eligible,
            status=overall_status,
            reasons=reasons,
            failed_filters=failed_filters,
            details=details,
        )
