"""Local tool-execution harness.

Each tool is a pure async function over an AsyncSession; the harness records an
AuditLog row for every call and publishes SSE events so the frontend can watch
the agent think in real time.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import events
from ..models import AuditLog, Milestone, Workflow
from . import planner

# JSON Schemas advertised to the Anthropic tool-use API.
TOOL_SCHEMAS: list[dict] = [
    {
        "name": "generate_roadmap",
        "description": "Generate the baseline 30/60/90-day onboarding roadmap for the workflow's role and tech stack, replacing any existing pending milestones.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_workflow_state",
        "description": "Fetch the workflow and its milestones with statuses.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "update_milestone_status",
        "description": "Set a milestone's status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "milestone_id": {"type": "integer"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "adapted"],
                },
            },
            "required": ["milestone_id", "status"],
        },
    },
    {
        "name": "adapt_roadmap",
        "description": "Re-plan remaining milestones in response to a disruption or acceleration event (e.g. laptop_delayed, first_pr_merged, mentor_out).",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "description": "Snake-case event identifier.",
                },
                "reason": {
                    "type": "string",
                    "description": "Human-readable rationale for the adaptation.",
                },
            },
            "required": ["event_type"],
        },
    },
]


async def _audit(session: AsyncSession, workflow_id: int, action: str, payload: dict) -> None:
    session.add(AuditLog(workflow_id=workflow_id, action_type=action, payload=payload))


async def _workflow_state(session: AsyncSession, workflow_id: int) -> dict:
    wf = await session.get(Workflow, workflow_id)
    if wf is None:
        raise ValueError(f"workflow {workflow_id} not found")
    result = await session.execute(
        select(Milestone).where(Milestone.workflow_id == workflow_id).order_by(Milestone.id)
    )
    return {
        "id": wf.id,
        "user_name": wf.user_name,
        "role": wf.role,
        "tech_stack": wf.tech_stack,
        "status": wf.status,
        "milestones": [
            {
                "id": m.id,
                "title": m.title,
                "timeline_bucket": m.timeline_bucket,
                "status": m.status,
                "description": m.description,
                "dependencies": m.dependencies,
            }
            for m in result.scalars()
        ],
    }


async def _tool_generate_roadmap(session: AsyncSession, workflow_id: int, _: dict) -> dict:
    wf = await session.get(Workflow, workflow_id)
    if wf is None:
        raise ValueError(f"workflow {workflow_id} not found")

    # Replace outstanding milestones; completed history is preserved.
    existing = await session.execute(
        select(Milestone).where(
            Milestone.workflow_id == workflow_id,
            Milestone.status != "completed",
        )
    )
    for m in existing.scalars():
        await session.delete(m)
    await session.flush()

    plan = planner.generate_roadmap(wf.role, wf.tech_stack)
    for m in plan:
        session.add(Milestone(workflow_id=workflow_id, **m))
    wf.status = "in_progress"
    await session.flush()
    return {"created": len(plan), "milestones": plan}


async def _tool_get_workflow_state(session: AsyncSession, workflow_id: int, _: dict) -> dict:
    return await _workflow_state(session, workflow_id)


async def _tool_update_milestone_status(
    session: AsyncSession, workflow_id: int, args: dict
) -> dict:
    milestone = await session.get(Milestone, int(args["milestone_id"]))
    if milestone is None or milestone.workflow_id != workflow_id:
        raise ValueError(f"milestone {args['milestone_id']} not found in workflow {workflow_id}")
    milestone.status = args["status"]
    await session.flush()
    return {"milestone_id": milestone.id, "status": milestone.status}


async def _tool_adapt_roadmap(session: AsyncSession, workflow_id: int, args: dict) -> dict:
    state = await _workflow_state(session, workflow_id)
    pending = [m for m in state["milestones"] if m["status"] in ("pending", "in_progress")]
    plan = planner.adapt_plan(pending, args["event_type"])

    by_title = {m["title"]: m for m in state["milestones"]}
    changed: list[dict] = []

    for m in plan["new_milestones"]:
        row = Milestone(workflow_id=workflow_id, **m)
        session.add(row)
        changed.append({"op": "insert", "title": m["title"]})

    for title, status in plan["status_updates"].items():
        if title in by_title:
            mid = by_title[title]["id"]
            row = await session.get(Milestone, mid)
            if row:
                row.status = status
                changed.append({"op": "status", "title": title, "status": status})

    for title, bucket in plan["bucket_moves"].items():
        if title in by_title and by_title[title]["status"] not in ("completed",):
            mid = by_title[title]["id"]
            row = await session.get(Milestone, mid)
            if row and row.status == "pending":
                row.timeline_bucket = bucket
                row.status = "adapted"
                changed.append({"op": "move", "title": title, "bucket": bucket})

    wf = await session.get(Workflow, workflow_id)
    if wf:
        wf.status = "adapted"
    await session.flush()
    return {"summary": plan["summary"], "changes": changed}


_DISPATCH = {
    "generate_roadmap": _tool_generate_roadmap,
    "get_workflow_state": _tool_get_workflow_state,
    "update_milestone_status": _tool_update_milestone_status,
    "adapt_roadmap": _tool_adapt_roadmap,
}


async def execute_tool(
    session: AsyncSession, workflow_id: int, name: str, args: dict[str, Any]
) -> dict[str, Any]:
    """Run one tool call: publish SSE, execute, audit, return result."""
    if name not in _DISPATCH:
        raise ValueError(f"unknown tool '{name}'")

    await events.publish(workflow_id, "tool_call", {"name": name, "input": args})
    result = await _DISPATCH[name](session, workflow_id, args)
    await _audit(session, workflow_id, f"tool:{name}", {"input": args, "result": result})
    await session.commit()
    await events.publish(
        workflow_id, "tool_result", {"name": name, "result": result}
    )
    return result
