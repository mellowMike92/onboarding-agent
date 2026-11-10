import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import StreamingResponse

from .. import events
from ..agent.agent import run_agent
from ..db import get_session
from ..models import AuditLog, Workflow
from ..schemas import AgentRunRequest, AuditLogOut, WorkflowCreate, WorkflowOut

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("", response_model=list[WorkflowOut])
async def list_workflows(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Workflow).options(selectinload(Workflow.milestones)).order_by(Workflow.id.desc())
    )
    return result.scalars().all()


@router.post("", response_model=WorkflowOut, status_code=201)
async def create_workflow(
    body: WorkflowCreate, session: AsyncSession = Depends(get_session)
):
    wf = Workflow(**body.model_dump())
    session.add(wf)
    await session.commit()
    result = await session.execute(
        select(Workflow)
        .options(selectinload(Workflow.milestones))
        .where(Workflow.id == wf.id)
    )
    return result.scalar_one()


@router.get("/{workflow_id}", response_model=WorkflowOut)
async def get_workflow(workflow_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Workflow)
        .options(selectinload(Workflow.milestones))
        .where(Workflow.id == workflow_id)
    )
    wf = result.scalar_one_or_none()
    if wf is None:
        raise HTTPException(404, "workflow not found")
    return wf


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(workflow_id: int, session: AsyncSession = Depends(get_session)):
    wf = await session.get(Workflow, workflow_id)
    if wf is None:
        raise HTTPException(404, "workflow not found")
    await session.delete(wf)
    await session.commit()


@router.post("/{workflow_id}/run", status_code=202)
async def run_workflow_agent(
    workflow_id: int,
    body: AgentRunRequest,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(Workflow, workflow_id) is None:
        raise HTTPException(404, "workflow not found")
    asyncio.create_task(
        run_agent(workflow_id, {"instruction": body.instruction, "force_generate": True})
    )
    return {"status": "agent_started", "workflow_id": workflow_id}


@router.get("/{workflow_id}/stream")
async def stream_workflow(workflow_id: int, session: AsyncSession = Depends(get_session)):
    if await session.get(Workflow, workflow_id) is None:
        raise HTTPException(404, "workflow not found")

    async def gen():
        yield "event: ready\ndata: {}\n\n"
        async for item in events.stream(workflow_id):
            yield f"event: {item['event']}\ndata: {json.dumps(item['data'], default=str)}\n\n"
            if item["event"] == "done":
                break

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{workflow_id}/audit", response_model=list[AuditLogOut])
async def get_audit_log(workflow_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.workflow_id == workflow_id)
        .order_by(AuditLog.id)
    )
    return result.scalars().all()
