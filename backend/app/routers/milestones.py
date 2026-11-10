from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .. import events
from ..db import get_session
from ..models import AuditLog, Milestone
from ..schemas import MilestoneOut, MilestoneUpdate

router = APIRouter(prefix="/api/milestones", tags=["milestones"])


@router.patch("/{milestone_id}", response_model=MilestoneOut)
async def update_milestone(
    milestone_id: int,
    body: MilestoneUpdate,
    session: AsyncSession = Depends(get_session),
):
    milestone = await session.get(Milestone, milestone_id)
    if milestone is None:
        raise HTTPException(404, "milestone not found")

    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(milestone, field, value)

    session.add(
        AuditLog(
            workflow_id=milestone.workflow_id,
            action_type="milestone.manual_update",
            payload={"milestone_id": milestone_id, "updates": updates},
        )
    )
    await session.commit()
    await session.refresh(milestone)

    await events.publish(
        milestone.workflow_id,
        "milestone_updated",
        {
            "id": milestone.id,
            "title": milestone.title,
            "status": milestone.status,
            "timeline_bucket": milestone.timeline_bucket,
        },
    )
    return milestone
