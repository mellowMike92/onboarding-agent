from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TimelineBucket = Literal["30_day", "60_day", "90_day"]
Status = Literal["pending", "in_progress", "completed", "adapted"]


class WorkflowCreate(BaseModel):
    user_name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=120)
    tech_stack: str = ""


class MilestoneOut(BaseModel):
    id: int
    workflow_id: int
    title: str
    timeline_bucket: str
    status: str
    description: str
    dependencies: list

    model_config = {"from_attributes": True}


class WorkflowOut(BaseModel):
    id: int
    user_name: str
    role: str
    tech_stack: str
    status: str
    created_at: datetime
    updated_at: datetime
    milestones: list[MilestoneOut] = []

    model_config = {"from_attributes": True}


class MilestoneUpdate(BaseModel):
    status: Status | None = None
    title: str | None = None
    description: str | None = None
    timeline_bucket: TimelineBucket | None = None


class AuditLogOut(BaseModel):
    id: int
    workflow_id: int
    action_type: str
    payload: dict
    timestamp: datetime

    model_config = {"from_attributes": True}


class WebhookEvent(BaseModel):
    """Inbound event from an external system (HRIS, GitHub, ITSM, LMS)."""

    workflow_id: int
    source: str = Field(min_length=1, max_length=60)  # e.g. 'github', 'hris'
    event_type: str = Field(
        min_length=1, max_length=120
    )  # e.g. 'first_pr_merged', 'laptop_delayed'
    payload: dict = {}


class AgentRunRequest(BaseModel):
    instruction: str = "Kick off onboarding and generate the 30/60/90-day roadmap."
