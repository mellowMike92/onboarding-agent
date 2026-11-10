"""Async API tests: workflow CRUD, agent run, milestone updates, webhooks, SSE."""

import asyncio

from tests.conftest import wait_for


async def _fetch_with_milestones(client, workflow_id):
    wf = (await client.get(f"/api/workflows/{workflow_id}")).json()
    # selectinload issues separate SELECTs for the workflow and its milestones,
    # so a mid-commit snapshot can show new milestones with a stale status —
    # only accept once the workflow row reflects the settled write.
    if wf["milestones"] and wf["status"] in ("in_progress", "adapted"):
        return wf
    return None


async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["agent_mode"] == "mock"


async def test_create_and_get_workflow(client, workflow_id):
    resp = await client.get(f"/api/workflows/{workflow_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_name"] == "Ada Lovelace"
    assert body["role"] == "Backend Engineer"
    assert body["status"] == "pending"
    assert body["milestones"] == []


async def test_agent_run_generates_roadmap(client, workflow_id):
    resp = await client.post(
        f"/api/workflows/{workflow_id}/run",
        json={"instruction": "Generate the onboarding roadmap."},
    )
    assert resp.status_code == 202

    wf = await wait_for(lambda: _fetch_with_milestones(client, workflow_id))
    assert len(wf["milestones"]) >= 10
    buckets = {m["timeline_bucket"] for m in wf["milestones"]}
    assert buckets == {"30_day", "60_day", "90_day"}
    assert wf["status"] in ("in_progress", "adapted")

    audit = (await client.get(f"/api/workflows/{workflow_id}/audit")).json()
    actions = {a["action_type"] for a in audit}
    assert "tool:generate_roadmap" in actions


async def test_milestone_status_update(client, workflow_id):
    await client.post(f"/api/workflows/{workflow_id}/run", json={})
    milestones = (await wait_for(lambda: _fetch_with_milestones(client, workflow_id)))[
        "milestones"
    ]
    target = milestones[0]

    resp = await client.patch(
        f"/api/milestones/{target['id']}", json={"status": "completed"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


async def test_webhook_triggers_adaptation(client, workflow_id):
    await client.post(f"/api/workflows/{workflow_id}/run", json={})
    await wait_for(lambda: _fetch_with_milestones(client, workflow_id))

    resp = await client.post(
        "/api/webhooks/events",
        json={
            "workflow_id": workflow_id,
            "source": "itsm",
            "event_type": "laptop_delayed",
            "payload": {"eta_days": 10},
        },
    )
    assert resp.status_code == 202

    async def adapted():
        wf = (await client.get(f"/api/workflows/{workflow_id}")).json()
        titles = [m["title"] for m in wf["milestones"]]
        return wf if "Contingency: docs & training sprint" in titles else None

    wf = await wait_for(adapted)
    provision = next(
        m
        for m in wf["milestones"]
        if m["title"] == "Provision accounts & dev environment"
    )
    assert provision["timeline_bucket"] == "60_day"
    assert provision["status"] == "adapted"
    assert wf["status"] == "adapted"

    audit = (await client.get(f"/api/workflows/{workflow_id}/audit")).json()
    assert any(a["action_type"] == "webhook:itsm.laptop_delayed" for a in audit)


async def test_sse_stream_receives_agent_events(client, workflow_id):
    received = []

    async def listen():
        async with client.stream(
            "GET", f"/api/workflows/{workflow_id}/stream"
        ) as resp:
            assert resp.status_code == 200
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                    received.append(event)
                    if event == "done":
                        return

    listener = asyncio.create_task(listen())
    await asyncio.sleep(0.1)  # let the subscriber register
    await client.post(f"/api/workflows/{workflow_id}/run", json={})
    await asyncio.wait_for(listener, timeout=15)

    assert "tool_call" in received
    assert "tool_result" in received
    assert "done" in received


async def test_unknown_workflow_404(client):
    assert (await client.get("/api/workflows/99999")).status_code == 404
    assert (await client.post("/api/workflows/99999/run", json={})).status_code == 404
