"""Synthetic milestone-adaptation evals.

Deterministic checks that the planner produces complete, well-formed roadmaps
and adapts them correctly to disruption/acceleration events — the agent's core
quality contract, eval-style.
"""

from app.agent.planner import BUCKETS, adapt_plan, generate_roadmap


def test_roadmap_completeness_eval():
    plan = generate_roadmap("Backend Engineer", "Python, FastAPI")
    assert len(plan) >= 10
    assert {m["timeline_bucket"] for m in plan} == set(BUCKETS)
    assert all(m["status"] == "pending" for m in plan)


def test_dependencies_resolve_eval():
    """Every dependency title must reference a real milestone in the plan."""
    for role in ("Backend Engineer", "Data Scientist", "Engineering Manager", "Product Designer"):
        plan = generate_roadmap(role, "the stack")
        titles = {m["title"] for m in plan}
        for m in plan:
            for dep in m["dependencies"]:
                assert dep in titles, f"{role}: dangling dep '{dep}'"


def test_role_specialization_eval():
    cases = {
        "Data Scientist": "lineage",
        "Engineering Manager": "skip-level",
        "Product Designer": "design system",
    }
    for role, needle in cases.items():
        plan = generate_roadmap(role, "")
        extra = next(m for m in plan if m["title"].startswith("Role ramp"))
        assert needle in extra["description"].lower()


def test_laptop_delay_adaptation_eval():
    plan = generate_roadmap("Backend Engineer", "Python")
    pending = [m for m in plan if m["status"] == "pending"]
    result = adapt_plan(pending, "laptop_delayed")

    assert result["bucket_moves"]["Provision accounts & dev environment"] == "60_day"
    titles = [m["title"] for m in result["new_milestones"]]
    assert any("contingency" in t.lower() for t in titles)


def test_early_completion_adaptation_eval():
    plan = generate_roadmap("Backend Engineer", "Python")
    pending = [m for m in plan if m["status"] == "pending"]
    result = adapt_plan(pending, "first_pr_merged")

    assert result["status_updates"]["Ship first low-risk change"] == "completed"
    assert any("stretch" in m["title"].lower() for m in result["new_milestones"])


def test_unknown_event_eval():
    result = adapt_plan([], "mystery_event")
    assert result["new_milestones"][0]["timeline_bucket"] == "30_day"
    assert "triage" in result["new_milestones"][0]["title"].lower()
