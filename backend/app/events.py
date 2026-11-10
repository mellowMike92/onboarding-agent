"""In-process pub/sub bus that fans agent execution events out to SSE clients."""

import asyncio
from collections import defaultdict
from collections.abc import AsyncGenerator
from typing import Any

_subscribers: dict[int, set[asyncio.Queue]] = defaultdict(set)


def subscribe(workflow_id: int) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=500)
    _subscribers[workflow_id].add(q)
    return q


def unsubscribe(workflow_id: int, q: asyncio.Queue) -> None:
    _subscribers[workflow_id].discard(q)
    if not _subscribers[workflow_id]:
        _subscribers.pop(workflow_id, None)


async def publish(workflow_id: int, event: str, data: dict[str, Any]) -> None:
    for q in list(_subscribers.get(workflow_id, ())):
        if q.full():
            continue
        await q.put({"event": event, "data": data})


async def stream(workflow_id: int) -> AsyncGenerator[dict, None]:
    q = subscribe(workflow_id)
    try:
        while True:
            yield await q.get()
    finally:
        unsubscribe(workflow_id, q)
