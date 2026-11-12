"""Candidate resume and profile parser.

Extracts tech stack, experience grade, target roles, preferred work formats,
and other job-seeking preferences from unstructured Russian or English text.
"""

import re
from typing import List, Optional, Set
from hirify_mcp.models import CandidateProfile

# Comprehensive catalog of common tech skills across domains
TECH_SKILLS = [
    # Languages
    "python", "javascript", "typescript", "golang", "go", "rust", "java", "kotlin",
    "scala", "c++", "c#", ".net", "php", "ruby", "swift", "elixir", "clojure", "dart",
    "sql", "r", "bash", "solidity",

    # Backend frameworks & libraries
    "fastapi", "django", "flask", "aiohttp", "celery", "asyncio", "sqlalchemy", "pydantic",
    "express", "nestjs", "nodejs", "node", "spring", "spring boot", "gin", "fiber", "echo",
    "actix", "tokio", "asp.net", "laravel", "symfony", "ruby on rails", "rails",

    # Frontend
    "react", "vue", "vue.js", "angular", "svelte", "next.js", "nextjs", "nuxt", "nuxtjs",
    "redux", "zustand", "mobx", "tailwind", "css", "html", "sass", "webpack", "vite",

    # Databases & Caching
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch", "opensearch",
    "clickhouse", "cassandra", "sqlite", "neo4j", "kafka", "rabbitmq", "nats",

    # DevOps, Cloud & Infrastructure
    "docker", "docker-compose", "kubernetes", "k8s", "helm", "terraform", "ansible",
    "aws", "gcp", "azure", "ci/cd", "github actions", "gitlab ci", "jenkins",
    "prometheus", "grafana", "linux", "nginx",

    # Mobile
    "flutter", "react native", "ios", "android", "swiftui",

    # AI, ML & Data Science
    "pytorch", "tensorflow", "scikit-learn", "pandas", "numpy", "opencv", "llm",
    "langchain", "transformers", "spark", "hadoop", "airflow", "dbt",

    # QA & Testing
    "pytest", "unittest", "selenium", "playwright", "cypress", "postman", "jmeter",

    # Protocols & Arch
    "rest", "rest api", "graphql", "grpc", "microservices", "websocket", "websockets",
    "event-driven", "system design"
]

# Aliases and canonical normalization
CANONICAL_SKILL_MAP = {
    "postgres": "postgresql",
    "vue.js": "vue",
    "nextjs": "next.js",
    "nuxtjs": "nuxt",
    "node": "nodejs",
    "k8s": "kubernetes",
    "golang": "go",
    "spring boot": "spring",
    "docker-compose": "docker",
    "websockets": "websocket",
}

ROLE_KEYWORDS = {
    "backend": [r"\bbackend\b", r"\bбэкенд", r"\bбэкэнд", r"\bбэк\b", r"\bserver\b"],
    "frontend": [r"\bfrontend\b", r"\bфронтенд", r"\bфронтэнд", r"\bфронт\b", r"\bui/ux\b"],
    "fullstack": [r"\bfullstack\b", r"\bfull-stack\b", r"\bфулстек", r"\bфуллстек"],
    "devops": [r"\bdevops\b", r"\bдевопс", r"\bsre\b", r"\binfrastructure\b"],
    "qa": [r"\bqa\b", r"\bтестировщик", r"\bqa automation\b", r"\bтестирован", r"\baqa\b"],
    "data_science": [r"\bdata science\b", r"\bdata scientist\b", r"\bml engineer\b", r"\bдатасаентист", r"\bmachine learning\b"],
    "data_engineer": [r"\bdata engineer\b", r"\bдата инженер", r"\bde\b"],
    "mobile": [r"\bmobile\b", r"\bмобильн", r"\bios\b", r"\bandroid\b"],
    "product_manager": [r"\bproduct manager\b", r"\bпродакт", r"\bproduct owner\b"],
    "teamlead": [r"\bteamlead\b", r"\bтимлид", r"\btechlead\b", r"\bтехлид"],
}

GRADE_KEYWORDS = {
    "lead": [r"\blead\b", r"\bteamlead\b", r"\btechlead\b", r"\bтимлид", r"\bтехлид", r"\bруководитель команды\b", r"\bhead of\b", r"\barchitect\b", r"\bархитектор"],
    "senior": [r"\bsenior\b", r"\bсеньор", r"\bсениор", r"\bсиньор", r"\bсеньер", r"\bстарш"],
    "middle": [r"\bmiddle\b", r"\bмидл", r"\bмиддл"],
    "junior": [r"\bjunior\b", r"\bджун", r"\bджуниор", r"\bначинающ", r"\bстажер", r"\bintern\b"],
}

WORK_FORMAT_KEYWORDS = {
    "remote": [r"\bremote\b", r"\bудаленк", r"\bудаленн", r"\bудалёнк", r"\bудалённ", r"\bдистанционн", r"\bтелеработ"],
    "hybrid": [r"\bhybrid\b", r"\bгибрид"],
    "onsite": [r"\bonsite\b", r"\bon-site\b", r"\boffice\b", r"\bофис", r"\bв офисе\b"],
}

DELIM_PATTERN = r"[\s,;.:/()\[\]|+*!?'\"\\-]"


class ResumeParser:
    """Extracts candidate profile and search queries from text."""

    @classmethod
    def extract_skills(cls, text: str) -> List[str]:
        """Detect technical skills from text using boundary-safe matching."""
        normalized_text = text.lower()
        found: Set[str] = set()

        for skill in TECH_SKILLS:
            # Escape skill for regex
            escaped = re.escape(skill)
            # Match boundary or surrounding whitespace / punctuation
            pattern = rf"(?:^|{DELIM_PATTERN}){escaped}(?:{DELIM_PATTERN}|$)"
            if re.search(pattern, normalized_text):
                canonical = CANONICAL_SKILL_MAP.get(skill, skill)
                found.add(canonical)

        return sorted(list(found))

    @classmethod
    def extract_grade(cls, text: str) -> Optional[str]:
        """Determine seniority grade from explicit mentions or years of experience."""
        normalized_text = text.lower()

        # Check explicit keywords
        for grade, patterns in GRADE_KEYWORDS.items():
            for pat in patterns:
                if re.search(pat, normalized_text):
                    return grade

        # Check experience in years (guard against calendar years like 2023, 2024)
        # e.g., "5 лет опыта", "1.5 года опыта", "5 years of experience", "опыт 6+ лет"
        exp_matches = re.finditer(r"(\d+(?:[.,]\d+)?)\s*\+?\s*(?:лет|года|год|years?)\b", normalized_text)
        for m in exp_matches:
            raw_val = m.group(1).replace(",", ".")
            try:
                years = float(raw_val)
                # Ignore calendar years like 1999, 2024
                if years > 40:
                    continue
                if years >= 5:
                    return "senior"
                elif years >= 2:
                    return "middle"
                elif years >= 0:
                    return "junior"
            except ValueError:
                continue

        return None

    @classmethod
    def extract_roles(cls, text: str) -> List[str]:
        """Determine primary role/specialization."""
        normalized_text = text.lower()
        matched_roles = []
        for role, patterns in ROLE_KEYWORDS.items():
            for pat in patterns:
                if re.search(pat, normalized_text):
                    matched_roles.append(role)
                    break
        return matched_roles

    @classmethod
    def extract_work_formats(cls, text: str) -> List[str]:
        """Detect preference for remote / hybrid / onsite."""
        normalized_text = text.lower()
        matched_formats = []
        for fmt, patterns in WORK_FORMAT_KEYWORDS.items():
            for pat in patterns:
                if re.search(pat, normalized_text):
                    matched_formats.append(fmt)
                    break
        return matched_formats

    @classmethod
    def parse_profile(cls, text: str) -> CandidateProfile:
        """Fully parse unstructured resume or intro text into CandidateProfile."""
        skills = cls.extract_skills(text)
        grade = cls.extract_grade(text)
        roles = cls.extract_roles(text)
        work_formats = cls.extract_work_formats(text)

        return CandidateProfile(
            raw_text=text,
            roles=roles,
            skills=skills,
            grade=grade,
            work_formats=work_formats,
        )
