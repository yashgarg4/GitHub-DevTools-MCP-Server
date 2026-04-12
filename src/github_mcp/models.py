"""Pydantic models for structured AI output validation."""

from pydantic import BaseModel, Field


# --- Code Review Models ---


class CodeBug(BaseModel):
    line: int | None = Field(None, description="Line number where the bug occurs")
    severity: str = Field(
        ..., description="Bug severity: 'critical', 'warning', or 'info'"
    )
    description: str = Field(..., description="What the bug is")


class CodeSuggestion(BaseModel):
    description: str = Field(..., description="What to improve")
    category: str = Field(
        ...,
        description="One of: 'performance', 'readability', 'security', 'best-practice'",
    )


class CodeReviewResult(BaseModel):
    bugs: list[CodeBug] = Field(default_factory=list)
    suggestions: list[CodeSuggestion] = Field(default_factory=list)
    quality_score: int = Field(..., ge=1, le=10, description="Code quality score 1-10")
    summary: str = Field(..., description="Brief overall assessment")


# --- Repository Health Check Models ---


class HealthScore(BaseModel):
    overall: int = Field(..., ge=1, le=10, description="Overall health score")
    maintenance: int = Field(
        ..., ge=1, le=10, description="Based on last push, stale issues/PRs"
    )
    ci_cd: int = Field(
        ..., ge=1, le=10, description="Based on workflow run success rate"
    )
    documentation: int = Field(
        ..., ge=1, le=10, description="Based on README completeness"
    )
    community: int = Field(
        ..., ge=1, le=10, description="Based on stars, forks, contributor activity"
    )


class HealthRisk(BaseModel):
    area: str = Field(..., description="Area of concern")
    severity: str = Field(..., description="'high', 'medium', or 'low'")
    description: str = Field(..., description="What the risk is")
    recommendation: str = Field(..., description="How to address it")


class RepoHealthReport(BaseModel):
    scores: HealthScore
    risks: list[HealthRisk] = Field(default_factory=list)
    summary: str = Field(..., description="Executive summary of repository health")
