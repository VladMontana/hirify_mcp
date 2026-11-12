"""Canonical normalization utilities for tech skills, grades, roles, and currencies."""

from typing import Dict, List, Optional

# Canonical mapping for tech skills
CANONICAL_SKILL_MAP: Dict[str, str] = {
    # Databases & Caches
    "postgres": "postgresql",
    "pgsql": "postgresql",
    "postgres sql": "postgresql",
    "mongo": "mongodb",
    "elastic": "elasticsearch",
    "opensearch": "elasticsearch",
    "click house": "clickhouse",
    "ms sql": "mssql",
    "sql server": "mssql",
    # Languages & Runtimes
    "golang": "go",
    "node": "nodejs",
    "node.js": "nodejs",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "cpp": "c++",
    "c plus plus": "c++",
    "c-sharp": "c#",
    "csharp": "c#",
    "dotnet": ".net",
    # Frameworks & Libs
    "fast-api": "fastapi",
    "vue.js": "vue",
    "vuejs": "vue",
    "nextjs": "next.js",
    "nuxtjs": "nuxt",
    "nuxt.js": "nuxt",
    "react.js": "react",
    "reactjs": "react",
    "spring boot": "spring",
    "springboot": "spring",
    "ror": "ruby on rails",
    "rails": "ruby on rails",
    "express.js": "express",
    "expressjs": "express",
    "nest": "nestjs",
    "nest.js": "nestjs",
    # DevOps & Infra
    "k8s": "kubernetes",
    "kube": "kubernetes",
    "docker compose": "docker-compose",
    "docker-compose": "docker-compose",
    "gh actions": "github actions",
    "gitlab-ci": "gitlab ci",
    # Protocols & Concepts
    "websockets": "websocket",
    "restful": "rest",
    "rest api": "rest",
    "rest-api": "rest",
}

# Distinct skills catalog with token boundaries
KNOWN_TECH_SKILLS: List[str] = [
    # Languages (special handling for symbols)
    "python",
    "javascript",
    "typescript",
    "golang",
    "go",
    "rust",
    "java",
    "kotlin",
    "scala",
    "c++",
    "c#",
    ".net",
    "php",
    "ruby",
    "swift",
    "elixir",
    "clojure",
    "dart",
    "sql",
    "r",
    "bash",
    "solidity",
    "perl",
    "haskell",
    # Backend frameworks
    "fastapi",
    "django",
    "flask",
    "aiohttp",
    "celery",
    "asyncio",
    "sqlalchemy",
    "pydantic",
    "express",
    "nestjs",
    "nodejs",
    "node",
    "spring",
    "spring boot",
    "gin",
    "fiber",
    "echo",
    "actix",
    "tokio",
    "asp.net",
    "laravel",
    "symfony",
    "ruby on rails",
    "rails",
    "grpc",
    # Frontend
    "react",
    "vue",
    "vue.js",
    "angular",
    "svelte",
    "next.js",
    "nextjs",
    "nuxt",
    "nuxtjs",
    "redux",
    "zustand",
    "mobx",
    "tailwind",
    "css",
    "html",
    "sass",
    "webpack",
    "vite",
    # Databases & Queues
    "postgresql",
    "postgres",
    "mysql",
    "mongodb",
    "redis",
    "elasticsearch",
    "opensearch",
    "clickhouse",
    "cassandra",
    "sqlite",
    "neo4j",
    "kafka",
    "rabbitmq",
    "nats",
    # DevOps, Cloud & Infra
    "docker",
    "docker-compose",
    "docker compose",
    "kubernetes",
    "k8s",
    "helm",
    "terraform",
    "ansible",
    "aws",
    "gcp",
    "azure",
    "ci/cd",
    "github actions",
    "gitlab ci",
    "jenkins",
    "prometheus",
    "grafana",
    "linux",
    "nginx",
    # Mobile
    "flutter",
    "react native",
    "ios",
    "android",
    "swiftui",
    # AI, ML & Data
    "pytorch",
    "tensorflow",
    "scikit-learn",
    "pandas",
    "numpy",
    "opencv",
    "llm",
    "langchain",
    "transformers",
    "spark",
    "hadoop",
    "airflow",
    "dbt",
    # QA & Testing
    "pytest",
    "unittest",
    "selenium",
    "playwright",
    "cypress",
    "postman",
    "jmeter",
    # Protocols & Architecture
    "rest",
    "rest api",
    "graphql",
    "microservices",
    "websocket",
    "websockets",
    "event-driven",
    "system design",
]

CANONICAL_GRADES: Dict[str, str] = {
    "intern": "trainee",
    "trainee": "trainee",
    "стажер": "trainee",
    "стажёр": "trainee",
    "практикант": "trainee",
    "junior": "junior",
    "джун": "junior",
    "джуниор": "junior",
    "начинающий": "junior",
    "middle": "middle",
    "мидл": "middle",
    "миддл": "middle",
    "senior": "senior",
    "сеньор": "senior",
    "сениор": "senior",
    "синьор": "senior",
    "старший": "senior",
    "lead": "lead",
    "teamlead": "lead",
    "techlead": "lead",
    "тимлид": "lead",
    "техлид": "lead",
    "ведущий": "lead",
    "head": "head",
    "head of": "head",
    "руководитель": "head",
    "director": "director",
    "директор": "director",
    "c_level": "c_level",
    "cto": "c_level",
    "cio": "c_level",
    "cpo": "c_level",
}

CANONICAL_WORK_FORMATS: Dict[str, str] = {
    "remote": "remote",
    "удаленка": "remote",
    "удалёнка": "remote",
    "удаленно": "remote",
    "удалённо": "remote",
    "дистанционно": "remote",
    "дистанционный": "remote",
    "телеработа": "remote",
    "home office": "remote",
    "hybrid": "hybrid",
    "гибрид": "hybrid",
    "гибридный": "hybrid",
    "onsite": "onsite",
    "on-site": "onsite",
    "office": "onsite",
    "офис": "onsite",
    "в офисе": "onsite",
}

# Role mapping to Hirify specialization codes
ROLE_TO_SPEC_CODE: Dict[str, str] = {
    "backend": "backend_dev",
    "frontend": "frontend_dev",
    "fullstack": "fullstack_dev",
    "devops": "devops",
    "sre": "sre",
    "qa": "qa_automation",
    "qa_automation": "qa_automation",
    "manual_qa": "manual_qa",
    "data_engineer": "data_engineering",
    "data_engineering": "data_engineering",
    "data_science": "data_science",
    "ai_engineering": "ai_engineering",
    "ml": "ai_engineering",
    "cybersecurity": "cybersecurity",
    "mobile": "mobile_development",
    "ios": "ios_dev",
    "android": "android_dev",
    "product_manager": "product_management",
    "project_manager": "project_management",
    "management": "engineering_management",
}

CANONICAL_CURRENCY: Dict[str, str] = {
    "$": "USD",
    "usd": "USD",
    "доллар": "USD",
    "долларов": "USD",
    "долл": "USD",
    "€": "EUR",
    "eur": "EUR",
    "евро": "EUR",
    "₽": "RUB",
    "rub": "RUB",
    "руб": "RUB",
    "рублей": "RUB",
    "rur": "RUB",
    "kzt": "KZT",
    "тенге": "KZT",
    "тг": "KZT",
    "£": "GBP",
    "gbp": "GBP",
    "фунт": "GBP",
    "cad": "CAD",
}


def normalize_skill(skill: str) -> str:
    """Normalize a single skill string to canonical form."""
    cleaned = skill.strip().lower()
    return CANONICAL_SKILL_MAP.get(cleaned, cleaned)


def normalize_grade(grade: Optional[str]) -> Optional[str]:
    """Normalize grade to canonical form (trainee, junior, middle, senior, lead, etc.)."""
    if not grade:
        return None
    cleaned = grade.strip().lower()
    return CANONICAL_GRADES.get(cleaned, cleaned)


def normalize_work_format(fmt: str) -> Optional[str]:
    """Normalize work format string to remote, hybrid, or onsite."""
    cleaned = fmt.strip().lower()
    return CANONICAL_WORK_FORMATS.get(cleaned, None)


def normalize_currency(curr: Optional[str]) -> Optional[str]:
    """Normalize currency symbol or name to standard 3-letter ISO code."""
    if not curr:
        return None
    cleaned = curr.strip().lower()
    return CANONICAL_CURRENCY.get(cleaned, curr.upper())


def role_to_hirify_spec(role: str) -> Optional[str]:
    """Convert human role name to Hirify API specialization code."""
    cleaned = role.strip().lower()
    return ROLE_TO_SPEC_CODE.get(cleaned, None)
