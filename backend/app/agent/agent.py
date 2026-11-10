"""Agent orchestration.

Two modes sharing the same tool harness and SSE stream:
- 'live': Anthropic tool-use loop (Claude decides which tools to call).
- 'mock': deterministic script that exercises the same tools, so the whole
  product works with no API key and evals stay reproducible.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from .. import events
from ..config import settings
from ..db import SessionLocal
from . import tools

SYSTEM_PROMPT = """You are an onboarding workflow agent. You manage a new hire's 30/60/90-day
onboarding roadmap using the provided tools.

Behavior:
- On kickoff: call generate_roadmap, then get_workflow_state, then summarize the plan.
- On external events: call adapt_roadmap with the event type, then get_workflow_state,
  then explain what changed and why.
- Keep answers concise and operational — this feeds a manager dashboard.
- Never invent milestones outside the tools; all state changes go through tool calls.
"""


async def _publish_msg(workflow_id: int, text: str) -> None:
    await events.publish(workflow_id, "agent_message", {"text": text})


async def _run_mock(workflow_id: int, context: dict[str, Any]) -> None:
    """Deterministic agent run: kickoff generates a roadmap; an event context
    triggers an adaptation pass."""
    async with SessionLocal() as session:
        state = await tools.execute_tool(
            session, workflow_id, "get_workflow_state", {}
        )
        event = context.get("event")

        if not state["milestones"] or context.get("force_generate"):
            await _publish_msg(
                workflow_id,
                f"Generating {state['role']} onboarding roadmap for {state['user_name']}…",
            )
            await asyncio.sleep(0.15)
            result = await tools.execute_tool(
                session, workflow_id, "generate_roadmap", {}
            )
            await _publish_msg(
                workflow_id,
                f"Roadmap created: {result['created']} milestones across 30/60/90-day buckets.",
            )
        elif event:
            await _publish_msg(
                workflow_id,
                f"Adapting roadmap to event '{event['event_type']}' from {event['source']}…",
            )
            await asyncio.sleep(0.15)
            result = await tools.execute_tool(
                session,
                workflow_id,
                "adapt_roadmap",
                {"event_type": event["event_type"], "reason": json.dumps(event.get("payload", {}))},
            )
            await _publish_msg(workflow_id, result["summary"])
        else:
            await _publish_msg(
                workflow_id,
                "Roadmap already up to date — no changes required.",
            )

        await tools.execute_tool(session, workflow_id, "get_workflow_state", {})


async def _run_live(workflow_id: int, context: dict[str, Any]) -> None:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    event = context.get("event")
    user_prompt = (
        context.get("instruction")
        or f"External event received: {event['event_type']} from {event['source']}. "
        f"Payload: {json.dumps(event.get('payload', {}))}. Adapt the roadmap."
    )

    messages: list[dict] = [{"role": "user", "content": user_prompt}]
    async with SessionLocal() as session:
        for _ in range(8):  # tool-loop guard
            resp = await client.messages.create(
                model=settings.anthropic_model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=tools.TOOL_SCHEMAS,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": resp.content})

            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            texts = [b.text for b in resp.content if b.type == "text" and b.text.strip()]
            for t in texts:
                await _publish_msg(workflow_id, t)

            if not tool_uses or resp.stop_reason == "end_turn":
                break

            tool_results = []
            for tu in tool_uses:
                try:
                    result = await tools.execute_tool(
                        session, workflow_id, tu.name, dict(tu.input)
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tu.id,
                            "content": json.dumps(result),
                        }
                    )
                except Exception as exc:  # surface tool errors back to the model
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tu.id,
                            "content": json.dumps({"error": str(exc)}),
                            "is_error": True,
                        }
                    )
            messages.append({"role": "user", "content": tool_results})


async def run_agent(workflow_id: int, context: dict[str, Any]) -> None:
    """Background entrypoint — always emits 'done' so SSE clients can settle."""
    try:
        await events.publish(
            workflow_id, "agent_status", {"status": "running", "mode": settings.agent_mode}
        )
        if settings.agent_mode == "live":
            await _run_live(workflow_id, context)
        else:
            await _run_mock(workflow_id, context)
        await events.publish(workflow_id, "agent_status", {"status": "done"})
    except Exception as exc:
        await events.publish(
            workflow_id, "agent_status", {"status": "error", "detail": str(exc)}
        )
    finally:
        await events.publish(workflow_id, "done", {})
