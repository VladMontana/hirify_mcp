"""Backward-compatible parser shim."""

from hirify_mcp.parsing.normalizer import (
    CANONICAL_GRADES,
    CANONICAL_SKILL_MAP,
    CANONICAL_WORK_FORMATS,
    normalize_skill,
)
from hirify_mcp.parsing.normalizer import (
    KNOWN_TECH_SKILLS as TECH_SKILLS,
)
from hirify_mcp.parsing.resume import ResumeParser

__all__ = [
    "TECH_SKILLS",
    "CANONICAL_SKILL_MAP",
    "CANONICAL_GRADES",
    "CANONICAL_WORK_FORMATS",
    "normalize_skill",
    "ResumeParser",
]
