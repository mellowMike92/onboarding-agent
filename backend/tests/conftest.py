import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["DATABASE_URL"] = (
    "sqlite+aiosqlite:///" + tempfile.mktemp(suffix="_test.db").replace("\\", "/")
)
os.environ.pop("ANTHROPIC_API_KEY", None)  # force deterministic mock agent

import asyncio

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db import init_db
from app.main import app


@pytest_asyncio.fixture
async def client():
    await init_db()  # ASGITransport does not run the app lifespan
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def workflow_id(client):
    resp = await client.post(
        "/api/workflows",
        json={
            "user_name": "Ada Lovelace",
            "role": "Backend Engineer",
            "tech_stack": "Python, FastAPI, Postgres",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def wait_for(predicate, timeout=10.0, interval=0.05):
    """Poll predicate() until it returns a truthy value or timeout."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        data = await predicate()
        if data:
            return data
        await asyncio.sleep(interval)
    raise TimeoutError("condition not met within timeout")
