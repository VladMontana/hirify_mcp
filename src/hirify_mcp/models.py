"""Pydantic data models for Hirify MCP server."""

from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TagItem(BaseModel):
    id: Optional[int] = None
    name: str


class GradeItem(BaseModel):
    id: Optional[int] = None
    name: str


class SpecializationItem(BaseModel):
    id: Optional[int] = None
    code: Optional[str] = None
    name: Optional[str] = None
    name_en: Optional[str] = None


class ContactItem(BaseModel):
    id: Optional[int] = None
    vacancy_id: Optional[int] = None
    type: Optional[str] = None
    url_type: Optional[str] = None
    value: Optional[str] = None
    short_code: Optional[str] = None


class SalaryItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    min: Optional[float] = Field(None, alias="from")
    max: Optional[float] = Field(None, alias="to")
    currency: Optional[str] = None
    salary_in_usd: Optional[float] = None
    salary_period: Optional[str] = None

    def __init__(self, **data: Any):
        # Support both 'min'/'max' from Hirify API and 'from'/'to'
        if "from" in data and "min" not in data:
            data["min"] = data["from"]
        if "to" in data and "max" not in data:
            data["max"] = data["to"]
        super().__init__(**data)


class VacancySummary(BaseModel):
    """Vacancy model as returned in listing/search."""
    model_config = ConfigDict(extra="ignore")

    id: int
    title: str
    slug: Optional[str] = None
    company_title: Optional[str] = None
    work_format: List[str] = Field(default_factory=list)
    work_type: Optional[str] = None
    remote_type: Optional[str] = None
    remote_restrictions: List[str] = Field(default_factory=list)
    allowed_locations: List[str] = Field(default_factory=list)
    contacts: List[ContactItem] = Field(default_factory=list)
    tags: List[TagItem] = Field(default_factory=list)
    grades: List[GradeItem] = Field(default_factory=list)
    specializations: List[SpecializationItem] = Field(default_factory=list)
    salary: Optional[SalaryItem] = None
    apply_url: Optional[str] = None
    can_apply_directly: Optional[bool] = None
    valid_through: Optional[str] = None
    is_archived: Optional[bool] = False

    @field_validator(
        "work_format",
        "remote_restrictions",
        "allowed_locations",
        "contacts",
        "tags",
        "grades",
        "specializations",
        mode="before",
    )
    @classmethod
    def ensure_list(cls, v: Any) -> List[Any]:
        return v if isinstance(v, list) else []

    @field_validator("salary", mode="before")
    @classmethod
    def parse_salary(cls, v: Any) -> Optional[SalaryItem]:
        if isinstance(v, SalaryItem):
            return v
        if isinstance(v, dict):
            return SalaryItem(**v)
        return None

    @property
    def url(self) -> str:
        """Full web link to the vacancy on hirify.me."""
        slug_part = self.slug or str(self.id)
        return f"https://hirify.me/jobs/{slug_part}"

    @property
    def tag_names(self) -> List[str]:
        return [t.name.lower() for t in self.tags if t.name]

    @property
    def grade_names(self) -> List[str]:
        return [g.name.lower() for g in self.grades if g.name]

    @property
    def salary_display(self) -> Optional[str]:
        """Human-readable salary string."""
        if not self.salary:
            return None
        curr = self.salary.currency or ""
        min_val = self.salary.min
        max_val = self.salary.max
        if min_val is not None and max_val is not None:
            return f"{int(min_val):,} - {int(max_val):,} {curr}".replace(",", " ").strip()
        elif min_val is not None:
            return f"от {int(min_val):,} {curr}".replace(",", " ").strip()
        elif max_val is not None:
            return f"до {int(max_val):,} {curr}".replace(",", " ").strip()
        return None


class VacancyDetails(VacancySummary):
    """Full vacancy description."""
    text: Optional[str] = None
    clear_text: Optional[str] = None
    tldr: Optional[str] = None
    main_stack: Optional[Any] = None
    application_instructions: Optional[str] = None
    english_level: Optional[str] = None
    nice_to_have_tags: List[Any] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    """Structured representation of candidate's skills and preferences."""
    raw_text: str
    roles: List[str] = Field(default_factory=list, description="Target job titles / roles (e.g. backend, frontend, qa)")
    skills: List[str] = Field(default_factory=list, description="Detected programming languages, tools, frameworks")
    grade: Optional[str] = Field(None, description="Seniority grade: junior, middle, senior, lead")
    work_formats: List[str] = Field(default_factory=list, description="Preferred formats: remote, hybrid, onsite")
    locations: List[str] = Field(default_factory=list, description="Preferred or resident locations/countries")
    min_salary: Optional[float] = Field(None, description="Minimum expected salary if detected")
    currency: Optional[str] = Field(None, description="Expected currency (USD, EUR, RUB, etc.)")


class MatchBreakdown(BaseModel):
    """Scoring component details."""
    skill_score: float = Field(0.0, description="Score based on mandatory & optional skills match (0-65)")
    grade_score: float = Field(0.0, description="Score based on grade alignment (0-20)")
    format_score: float = Field(0.0, description="Score based on remote/hybrid/onsite match (0-15)")


class MatchResult(BaseModel):
    """Result of matching candidate profile against a vacancy."""
    vacancy_id: int
    title: str
    company: str
    url: str
    total_score: int = Field(..., ge=0, le=100, description="Compatibility score percentage (0-100)")
    breakdown: MatchBreakdown
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    grade_match: str = Field(..., description="exact, close, mismatch, or unknown")
    format_match: bool = Field(True, description="Whether work format matches preferences")
    summary: str = Field(..., description="Short explanation why this vacancy is recommended or why points were deducted")
    contacts: List[str] = Field(default_factory=list, description="Direct URLs or contacts to apply")
    salary: Optional[str] = Field(None, description="Human-readable salary if specified")
