import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..agent.agent import run_agent
from ..db import get_session
from ..models import AuditLog, Workflow
from ..schemas import WebhookEvent

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/events", status_code=202)
async def ingest_event(
    body: WebhookEvent, session: AsyncSession = Depends(get_session)
):
    """Ingest an external system event (HRIS/GitHub/ITSM/LMS).

    The event is written to the audit trail, then the agent is woken to adapt
    the workflow's roadmap — the adaptation itself streams over SSE.
    """
    if await session.get(Workflow, body.workflow_id) is None:
        raise HTTPException(404, "workflow not found")

    session.add(
        AuditLog(
            workflow_id=body.workflow_id,
            action_type=f"webhook:{body.source}.{body.event_type}",
            payload=body.payload,
        )
    )
    await session.commit()

    asyncio.create_task(
        run_agent(
            body.workflow_id,
            {
                "event": {
                    "source": body.source,
                    "event_type": body.event_type,
                    "payload": body.payload,
                }
            },
        )
    )
    return {
        "status": "accepted",
        "workflow_id": body.workflow_id,
        "event_type": body.event_type,
    }
