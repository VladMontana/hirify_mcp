"""Candidate resume and profile parser with boundary-safe tokenization and heuristic analysis."""

import re
from typing import List, Optional, Set, Tuple

from hirify_mcp.models import CandidateProfile
from hirify_mcp.parsing.normalizer import (
    CANONICAL_GRADES,
    KNOWN_TECH_SKILLS,
    normalize_currency,
    normalize_grade,
    normalize_skill,
)

# Common country roots with Russian and English inflections
COUNTRY_ROOTS = {
    "росси": "russia",
    "рф": "russia",
    "russia": "russia",
    "беларус": "belarus",
    "белорусси": "belarus",
    "belarus": "belarus",
    "казахстан": "kazakhstan",
    "германи": "germany",
    "germany": "germany",
    "deutschland": "germany",
    "серби": "serbia",
    "serbia": "serbia",
    "грузи": "georgia",
    "georgia": "georgia",
    "армени": "armenia",
    "armenia": "armenia",
    "турци": "turkey",
    "turkey": "turkey",
    "сша": "united_states",
    "usa": "united_states",
    "united states": "united_states",
    "великобритани": "united_kingdom",
    "uk": "united_kingdom",
    "кипр": "cyprus",
    "cyprus": "cyprus",
    "польш": "poland",
    "poland": "poland",
}

ROLE_PATTERNS = {
    "backend": [r"\bbackend\b", r"\bбэкенд", r"\bбэкэнд", r"\bбэк\b", r"\bserver-side\b"],
    "frontend": [r"\bfrontend\b", r"\bфронтенд", r"\bфронтэнд", r"\bфронт\b"],
    "fullstack": [r"\bfullstack\b", r"\bfull-stack\b", r"\bфулстек", r"\bфуллстек"],
    "devops": [r"\bdevops\b", r"\bдевопс", r"\binfrastructure\b"],
    "sre": [r"\bsre\b", r"\bsite reliability\b"],
    "qa_automation": [
        r"\bqa automation\b",
        r"\baqa\b",
        r"\bавтотестиров",
        r"\bавтоматизаци[ия] тестирован",
    ],
    "manual_qa": [r"\bmanual qa\b", r"\bручн(?:ое|ый) тестиров", r"\bqa\b", r"\bтестировщик"],
    "data_engineering": [
        r"\bdata engineer\b",
        r"\bдата инженер",
        r"\betl\b",
        r"\bdata engineering\b",
    ],
    "data_science": [r"\bdata science\b", r"\bdata scientist\b", r"\bдатасаентист"],
    "ai_engineering": [
        r"\bai engineer\b",
        r"\bprompt engineer\b",
        r"\bllm engineer\b",
        r"\bml engineer\b",
        r"\bmachine learning\b",
    ],
    "cybersecurity": [
        r"\bcybersecurity\b",
        r"\bбезопасник\b",
        r"\bинформационная безопасность\b",
        r"\bappsec\b",
        r"\bsecops\b",
    ],
    "mobile": [r"\bmobile developer\b", r"\bмобильный разработчик\b", r"\bmobile dev\b"],
    "ios": [r"\bios developer\b", r"\bios-разработчик\b", r"\bios dev\b"],
    "android": [r"\bandroid developer\b", r"\bandroid-разработчик\b", r"\bandroid dev\b"],
}

ENGLISH_LEVELS = [
    (r"\b(?:c2|proficiency|native|носитель)\b", "c2"),
    (r"\b(?:c1|advanced|продвинутый)\b", "c1"),
    (r"\b(?:b2|upper-intermediate|выше среднего)\b", "b2"),
    (r"\b(?:b1|intermediate|средний)\b", "b1"),
    (r"\b(?:a2|pre-intermediate)\b", "a2"),
    (r"\b(?:a1|elementary|начальный)\b", "a1"),
]

ASPIRATION_PATTERNS = [
    r"(?:хочу|планирую|стремлюсь|мечтаю)\s+(?:стать|вырасти|дорасти|быть)\s+(?:до\s+)?(\w+)",
    r"(?:в будущем|в перспективе|цель[:\s]+)\s*(?:стать\s+)?(\w+)",
    r"(?:развива(?:юсь|ться)\s+до)\s+(\w+)",
]


class ResumeParser:
    """Robust parser for resumes, job-seeking intros, and candidate bios."""

    @classmethod
    def extract_skills(cls, text: str) -> List[str]:
        """Detect technical skills safely using token boundaries and disambiguation."""
        if not text:
            return []

        lower_text = text.lower()
        found: Set[str] = set()

        sorted_skills = sorted(KNOWN_TECH_SKILLS, key=len, reverse=True)

        for skill in sorted_skills:
            if skill == "c++":
                pattern = r"(?:^|[\s,;.:/()\[\]|+*!?'\"\\-])c\+\+(?:$|[\s,;.:/()\[\]|+*!?'\"\\-])"
            elif skill == "c#":
                pattern = r"(?:^|[\s,;.:/()\[\]|+*!?'\"\\-])c\#(?:$|[\s,;.:/()\[\]|+*!?'\"\\-])"
            elif skill == ".net":
                pattern = r"(?:^|[\s,;.:/()\[\]|+*!?'\"\\-])\.net(?:$|[\s,;.:/()\[\]|+*!?'\"\\-])"
            elif skill == "c":
                pattern = r"(?:^|[\s,;:/()\[\]|+*!?'\"\\-])c(?:$|[\s,;:/()\[\]|+*!?'\"\\-])"
            elif skill == "go":
                pattern = r"\bgo\b"
            elif skill == "node":
                pattern = r"\bnode(?:\.js)?\b"
            else:
                pattern = rf"\b{re.escape(skill)}\b"

            if re.search(pattern, lower_text):
                canonical = normalize_skill(skill)
                if skill == "c" and ("c++" in found or "c#" in found):
                    continue
                if skill == "react" and "react native" in lower_text:
                    found.add("react native")
                found.add(canonical)

        return sorted(list(found))

    @classmethod
    def extract_grade_and_experience(cls, text: str) -> Tuple[Optional[str], Optional[float], bool]:
        """Determine seniority grade, commercial experience in years, and whether commercial exp is present."""
        if not text:
            return None, None, False

        lower_text = text.lower()

        # 1. Check for explicit absence of commercial experience
        no_commercial_exp = bool(
            re.search(
                r"\b(?:коммерческого\s+опыта\s+(?:нет|не\s+имею|0)|"
                r"без\s+коммерческого\s+опыта|"
                r"опыт\s+только\s+(?:учебный|пет|pet|на\s+курсах)|"
                r"только\s+pet[- ]?проекты|"
                r"no\s+commercial\s+experience)\b",
                lower_text,
            )
        )

        # 2. Extract aspiration grades
        aspiration_grades = set()
        for asp_pat in ASPIRATION_PATTERNS:
            for match in re.finditer(asp_pat, lower_text):
                word = match.group(1).lower()
                normalized = normalize_grade(word)
                if normalized:
                    aspiration_grades.add(normalized)

        # 3. Check for explicitly targeted / current grade
        target_grade = None
        target_patterns = [
            r"\b(?:ищу|рассматриваю|позици(?:я|ю)|ваканси(?:я|ю)|на\s+роль)\s+(?:junior|джун|мидл|middle|senior|сеньор|lead|тимлид|intern|стажер)\b",
            r"\b(?:я|уровень|грейд)[:\s]+(?:junior|джун|мидл|middle|senior|сеньор|lead|тимлид|intern|стажер)\b",
            r"\b(junior|джун|джуниор|стажер|intern|middle|мидл|senior|сеньор|lead|тимлид)\s+(?:developer|разработчик|инженер|инженер-разработчик|backend|frontend|devops|qa)\b",
        ]
        for pat in target_patterns:
            m = re.search(pat, lower_text)
            if m:
                matched_str = m.group(0)
                for word in [
                    "intern",
                    "стажер",
                    "junior",
                    "джуниор",
                    "джун",
                    "middle",
                    "мидл",
                    "senior",
                    "сеньор",
                    "lead",
                    "тимлид",
                ]:
                    if word in matched_str:
                        candidate_grade = normalize_grade(word)
                        if candidate_grade not in aspiration_grades:
                            target_grade = candidate_grade
                            break
            if target_grade:
                break

        # 4. Extract commercial experience years
        exp_years: Optional[float] = None
        if not no_commercial_exp:
            exp_matches = re.finditer(
                r"(\d+(?:[.,]\d+)?)\s*\+?\s*(?:лет|года|год|years?)\s*(?:коммерческого\s+)?(?:опыта|работы|in\s+tech)?\b",
                lower_text,
            )
            for m in exp_matches:
                raw_val = m.group(1).replace(",", ".")
                try:
                    val = float(raw_val)
                    if 0 < val <= 40:
                        exp_years = val
                        break
                except ValueError:
                    continue

        has_commercial = (exp_years is not None and exp_years > 0) and not no_commercial_exp

        if target_grade:
            return target_grade, exp_years, has_commercial

        if no_commercial_exp:
            return "junior", 0.0, False

        if exp_years is not None:
            if exp_years >= 5:
                return "senior", exp_years, True
            elif exp_years >= 2:
                return "middle", exp_years, True
            elif exp_years >= 0.5:
                return "junior", exp_years, True
            else:
                return "trainee", exp_years, True

        for word, grade_val in CANONICAL_GRADES.items():
            if re.search(rf"\b{re.escape(word)}\b", lower_text):
                if grade_val not in aspiration_grades:
                    return grade_val, None, False

        return None, None, False

    @classmethod
    def extract_grade(cls, text: str) -> Optional[str]:
        """Legacy helper for backward compatibility."""
        grade, _, _ = cls.extract_grade_and_experience(text)
        return grade

    @classmethod
    def extract_roles(cls, text: str) -> List[str]:
        """Detect target job roles / disciplines."""
        if not text:
            return []
        lower_text = text.lower()
        matched = []
        for role, patterns in ROLE_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, lower_text):
                    matched.append(role)
                    break
        return matched

    @classmethod
    def extract_work_formats(cls, text: str) -> List[str]:
        """Legacy helper for extracting work formats."""
        fmts = cls.extract_preferences(text).get("work_formats", [])
        return [str(f) for f in fmts] if isinstance(fmts, list) else []

    @classmethod
    def extract_preferences(cls, text: str) -> dict:
        """Extract work format, remote only, salary expectations, english, and location."""
        if not text:
            return {}

        lower_text = text.lower()

        remote_only = bool(
            re.search(
                r"\b(?:только\s+удаленк[а-я]*|remote\s+only|строго\s+удаленк[а-я]*|"
                r"исключительно\s+удаленн[а-я]*|только\s+дистанционн[а-я]*)\b",
                lower_text,
            )
        )

        formats = []
        if re.search(
            r"\b(?:remote|удаленк[а-я]*|удаленн[а-я]*|удалёнк[а-я]*|удалённ[а-я]*|дистанционн[а-я]*|телеработ[а-я]*|home office)\b",
            lower_text,
        ):
            formats.append("remote")
        if re.search(r"\b(?:hybrid|гибрид[а-я]*)\b", lower_text):
            formats.append("hybrid")
        if re.search(r"\b(?:onsite|on-site|office|офис[а-я]*|в офисе)\b", lower_text):
            formats.append("onsite")

        if remote_only and "remote" not in formats:
            formats.append("remote")

        english_level = None
        for pat, level in ENGLISH_LEVELS:
            if re.search(pat, lower_text):
                english_level = level
                break

        min_salary = None
        currency = None

        # Targeted salary search
        sal_patterns = [
            r"(?:зарплат[а-я]*|salary|ожидания|з/п|доход)?\s*(?:от|from|min)[:\s]*([\$€₽£]?\s*\d{1,3}(?:[\s,]\d{3})*|\d+)\s*([\$€₽£]|usd|eur|rub|rur|kzt|gbp|cad|руб|долл|евро)?\b",
            r"([\$€₽£])\s*(\d{1,3}(?:[\s,]\d{3})*|\d+)",
            r"(\d{1,3}(?:[\s,]\d{3})*|\d+)\s*([\$€₽£]|usd|eur|rub|rur|kzt|gbp|cad|руб|долл|евро)\b",
        ]
        for pat in sal_patterns:
            m = re.search(pat, lower_text)
            if m:
                groups = m.groups()
                num_str = None
                curr_cand = None
                for g in groups:
                    if not g:
                        continue
                    clean_g = (
                        g.replace(" ", "")
                        .replace(",", "")
                        .replace("$", "")
                        .replace("€", "")
                        .replace("₽", "")
                        .replace("£", "")
                    )
                    if clean_g.isdigit():
                        num_str = clean_g
                    elif any(
                        c in g.lower()
                        for c in [
                            "usd",
                            "eur",
                            "rub",
                            "kzt",
                            "gbp",
                            "cad",
                            "руб",
                            "долл",
                            "евро",
                            "$",
                            "€",
                            "₽",
                            "£",
                        ]
                    ):
                        curr_cand = g
                if num_str:
                    val = float(num_str)
                    if 200 <= val <= 2_000_000 and not (1990 <= val <= 2035 and not curr_cand):
                        min_salary = val
                        currency = normalize_currency(curr_cand) if curr_cand else "USD"
                        break

        # Location matching by root
        detected_country = None
        for root, canonical_country in COUNTRY_ROOTS.items():
            if re.search(rf"\b{root}[а-я]*\b", lower_text):
                detected_country = canonical_country
                break

        return {
            "remote_only": remote_only,
            "work_formats": formats,
            "english_level": english_level,
            "min_salary": min_salary,
            "currency": currency,
            "current_country": detected_country,
        }

    @classmethod
    def parse_profile(cls, text: str) -> CandidateProfile:
        """Fully parse unstructured resume or text into CandidateProfile."""
        skills = cls.extract_skills(text)
        grade, exp_years, has_commercial = cls.extract_grade_and_experience(text)
        roles = cls.extract_roles(text)
        prefs = cls.extract_preferences(text)

        acceptable = []
        if grade == "junior":
            acceptable = ["trainee", "junior"]
        elif grade == "trainee":
            acceptable = ["trainee", "junior"]
        elif grade == "middle":
            acceptable = ["middle", "junior"]
        elif grade == "senior":
            acceptable = ["senior", "lead"]
        elif grade == "lead":
            acceptable = ["lead", "senior", "head"]

        return CandidateProfile(
            raw_text=text,
            roles=roles,
            skills=skills,
            grade=grade,
            acceptable_grades=acceptable,
            commercial_experience_years=exp_years,
            has_commercial_experience=has_commercial,
            work_formats=prefs.get("work_formats", []),
            remote_only=prefs.get("remote_only", False),
            english_level=prefs.get("english_level"),
            min_salary=prefs.get("min_salary"),
            currency=prefs.get("currency"),
            current_country=prefs.get("current_country"),
            legal_work_countries=[prefs["current_country"]] if prefs.get("current_country") else [],
        )
