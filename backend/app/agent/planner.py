"""Deterministic roadmap planner.

Used in two places: as the 'generate_roadmap' tool's knowledge source, and as the
whole agent's brain when running in mock mode (no ANTHROPIC_API_KEY). Keeping it
pure/declarative makes the eval suite deterministic.
"""

from __future__ import annotations

BUCKETS = ("30_day", "60_day", "90_day")

_BASE_ROADMAP: dict[str, list[dict]] = {
    "30_day": [
        {
            "title": "Provision accounts & dev environment",
            "description": "SSO, VPN, repo access, and a reproducible local dev environment for {stack}.",
            "dependencies": [],
        },
        {
            "title": "Complete security & compliance training",
            "description": "Required infosec, code-of-conduct, and data-handling modules in the LMS.",
            "dependencies": ["Provision accounts & dev environment"],
        },
        {
            "title": "Meet manager, mentor & buddy pair",
            "description": "Set recurring 1:1s, agree on communication norms, and review the 30/60/90 plan.",
            "dependencies": [],
        },
        {
            "title": "Ship first low-risk change",
            "description": "Land a small {stack} PR end-to-end: branch, review, CI, deploy pipeline.",
            "dependencies": ["Provision accounts & dev environment"],
        },
    ],
    "60_day": [
        {
            "title": "Own a scoped feature end-to-end",
            "description": "Design, implement, test, and ship a bounded feature in the {stack} codebase.",
            "dependencies": ["Ship first low-risk change"],
        },
        {
            "title": "Shadow on-call & incident process",
            "description": "Pair through one incident/alert cycle; document runbook gaps found.",
            "dependencies": [],
        },
        {
            "title": "Present a tech deep-dive to the team",
            "description": "Walk the team through one subsystem's architecture and trade-offs.",
            "dependencies": [],
        },
    ],
    "90_day": [
        {
            "title": "Independently deliver a milestone project",
            "description": "Drive a quarterly-scoped deliverable with minimal supervision.",
            "dependencies": ["Own a scoped feature end-to-end"],
        },
        {
            "title": "Join the on-call rotation",
            "description": "Take primary on-call shifts after sign-off from the incident lead.",
            "dependencies": ["Shadow on-call & incident process"],
        },
        {
            "title": "30/60/90 review & goal setting",
            "description": "Retro the onboarding plan with manager; set next-quarter OKRs.",
            "dependencies": [],
        },
    ],
}

_ROLE_TEMPLATES: dict[str, dict[str, str]] = {
    "engineer": {
        "30_extra": "Pair-program through the team's core service with a senior engineer.",
    },
    "data": {
        "30_extra": "Rebuild one production dashboard query locally and explain its lineage.",
    },
    "manager": {
        "30_extra": "Run skip-level 1:1s with every direct report and summarize themes.",
    },
    "designer": {
        "30_extra": "Audit the design system and flag three consistency gaps.",
    },
}


def _role_key(role: str) -> str:
    r = role.lower()
    if any(k in r for k in ("manager", "lead", "director", "head")):
        return "manager"
    if "data" in r or "ml" in r or "ai" in r:
        return "data"
    if "design" in r:
        return "designer"
    return "engineer"


def generate_roadmap(role: str, tech_stack: str) -> list[dict]:
    """Return the baseline 30/60/90 milestone template for a role."""
    stack = tech_stack or "the team's stack"
    key = _role_key(role)
    milestones: list[dict] = []
    for bucket in BUCKETS:
        for item in _BASE_ROADMAP[bucket]:
            milestones.append(
                {
                    "title": item["title"],
                    "timeline_bucket": bucket,
                    "status": "pending",
                    "description": item["description"].format(stack=stack),
                    "dependencies": list(item["dependencies"]),
                }
            )
    extra = _ROLE_TEMPLATES[key]["30_extra"]
    milestones.insert(
        2,
        {
            "title": f"Role ramp: {role}",
            "timeline_bucket": "30_day",
            "status": "pending",
            "description": extra,
            "dependencies": ["Provision accounts & dev environment"],
        },
    )
    return milestones


_EVENT_ADAPTATIONS: dict[str, dict] = {
    "laptop_delayed": {
        "summary": "Hardware delay detected — front-loading non-laptop work",
        "new_milestones": [
            {
                "title": "Contingency: docs & training sprint",
                "timeline_bucket": "30_day",
                "description": "While hardware is in transit, front-load handbook, architecture docs, and LMS modules that only need a browser.",
                "dependencies": [],
            }
        ],
        "bump_titles": ["Provision accounts & dev environment"],
        "bump_to": "60_day",
    },
    "first_pr_merged": {
        "summary": "First PR merged early — accelerating technical milestones",
        "new_milestones": [
            {
                "title": "Stretch: tackle a second, medium-risk PR",
                "timeline_bucket": "30_day",
                "description": "Ahead of plan — pull forward a medium-complexity change to build momentum.",
                "dependencies": ["Ship first low-risk change"],
            }
        ],
        "shift_to": {"Ship first low-risk change": "completed"},
    },
    "mentor_out": {
        "summary": "Mentor unavailable — reassigning pairing sessions",
        "new_milestones": [
            {
                "title": "Reassign mentor & reschedule pairing",
                "timeline_bucket": "30_day",
                "description": "Manager to nominate a backup mentor; reschedule the blocked pairing sessions.",
                "dependencies": [],
            }
        ],
        "bump_titles": ["Meet manager, mentor & buddy pair"],
        "bump_to": "60_day",
    },
    "security_blocker": {
        "summary": "Access/security blocker — adding escalation path",
        "new_milestones": [
            {
                "title": "Escalate access blocker to IT security",
                "timeline_bucket": "30_day",
                "description": "Open expedited ITSM ticket and notify manager; re-sequence blocked tasks.",
                "dependencies": [],
            }
        ],
        "bump_titles": ["Ship first low-risk change"],
        "bump_to": "60_day",
    },
}


def adapt_plan(
    pending_milestones: list[dict], event_type: str
) -> dict:
    """Given pending milestones + an external event type, produce an adaptation.

    Returns {'summary', 'new_milestones': [...], 'status_updates': {title: status},
    'bucket_moves': {title: bucket}}. Unknown events get a generic re-plan.
    """
    rule = _EVENT_ADAPTATIONS.get(event_type)
    if rule is None:
        return {
            "summary": f"Unrecognized event '{event_type}' — inserted a triage milestone",
            "new_milestones": [
                {
                    "title": f"Triage external event: {event_type}",
                    "timeline_bucket": "30_day",
                    "description": "Agent flagged an unmapped workflow event; manager reviews impact on the plan.",
                    "dependencies": [],
                }
            ],
            "status_updates": {},
            "bucket_moves": {},
        }

    status_updates = dict(rule.get("shift_to", {}))
    bucket_moves = {
        t: rule["bump_to"] for t in rule.get("bump_titles", [])
    }
    return {
        "summary": rule["summary"],
        "new_milestones": [dict(m, status="pending") for m in rule["new_milestones"]],
        "status_updates": status_updates,
        "bucket_moves": bucket_moves,
    }
