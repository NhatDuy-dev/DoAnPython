"""Single source of truth for the TV2 integration contract."""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class AssignmentStatus(str, Enum):
    ASSIGNED = "assigned"
    REJECTED = "rejected"
    RELEASED = "released"


class PullRequestIn(BaseModel):
    pr_id: str = Field(min_length=1)
    author_id: str = Field(min_length=1)
    repository: str = Field(min_length=1)
    changed_files: List[str] = Field(min_length=1)
    quality_score: Optional[float] = Field(default=None, ge=0, le=100)
    risk_score: Optional[float] = Field(default=None, ge=0, le=100)
    required_reviewers: Optional[int] = Field(default=None, ge=1, le=20)

    @field_validator("changed_files")
    @classmethod
    def non_empty_files(cls, value: List[str]) -> List[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("changed_files must contain at least one path")
        return cleaned


class ReviewerIn(BaseModel):
    reviewer_id: str = Field(min_length=1)
    expertise: List[str] = Field(default_factory=list)
    is_available: bool = True
    current_load: int = Field(default=0, ge=0)
    max_load: int = Field(default=3, ge=1)

    @field_validator("expertise")
    @classmethod
    def clean_expertise(cls, value: List[str]) -> List[str]:
        return sorted({item.strip().lower() for item in value if item.strip()})


class ReviewerPatch(BaseModel):
    expertise: Optional[List[str]] = None
    is_available: Optional[bool] = None
    current_load: Optional[int] = Field(default=None, ge=0)
    max_load: Optional[int] = Field(default=None, ge=1)


class AssignmentView(BaseModel):
    assignment_id: int
    pr_id: str
    reviewer_id: str
    status: AssignmentStatus
    score: float
    matched_files: List[str]
    reasons: List[str]


class AssignmentResult(BaseModel):
    pr_id: str
    status: str
    requested: int
    assigned: int
    message: str
    assignments: List[AssignmentView]

