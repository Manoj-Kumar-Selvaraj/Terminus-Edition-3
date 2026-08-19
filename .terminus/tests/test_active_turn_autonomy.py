"""Regression coverage for active-turn run-to-blocker orchestration."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = ROOT / ".terminus"
POLICY = T / "agents" / "ACTIVE_TURN_AUTONOMY.md"
CONTINUE = T / "CONTINUE_SESSION.md"
PROJECT_AGENT = ROOT / ".cursor" / "agents" / "terminus-ci-orchestrator.md"


def test_active_turn_policy_requires_run_to_blocker() -> None:
    text = POLICY.read_text(encoding="utf-8")
    for marker in (
        "Active-turn autonomy policy version: `1.0`",
        "The default active-turn policy is `RUN_TO_BLOCKER`",
        "A routing cycle completing is not a response-completion condition",
        "immediately call or reconstruct the current `controller_cli continue` result",
        "a legal already-authorized next action remains executable",
        "If no legal stop reason exists, continue working instead of finishing the response",
    ):
        assert marker in text


def test_dispatched_or_running_actions_are_not_stop_conditions() -> None:
    text = POLICY.read_text(encoding="utf-8")
    for marker in (
        "an already-authorized GitHub Actions workflow was dispatched",
        "`queued`, `pending`, `waiting`, `requested`, or `in_progress`",
        "poll it to a terminal state",
        "A queued/running workflow is never a blocker merely because foreground time has elapsed",
        "There is no autonomous active-turn timeout policy",
    ):
        assert marker in text


def test_policy_preserves_real_manual_and_authorization_boundaries() -> None:
    text = POLICY.read_text(encoding="utf-8")
    for marker in (
        "Manual independent role boundary",
        "Human decision or authorization boundary",
        "External gate unable to advance now",
        "Circuit breaker or policy blocker",
        "Required evidence/tool unavailable",
        "Active execution surface involuntarily ends",
    ):
        assert marker in text


def test_policy_does_not_move_normal_producers_to_paid_hosted_backends() -> None:
    text = POLICY.read_text(encoding="utf-8")
    for marker in (
        "does **not** introduce a hosted producer backend",
        "normal producer/fixer and routed Q1/Q2/Q3/Q5/Q7 work remains same-task-chat",
        "Q4/Q6 remain independent",
        "Q8 remains governed only by `TERMINUS_Q8_MODE`",
        "provider fallback and verdict shopping remain forbidden",
    ):
        assert marker in text


def test_bootstrap_and_project_agent_bind_active_turn_policy() -> None:
    continuation = CONTINUE.read_text(encoding="utf-8")
    agent = PROJECT_AGENT.read_text(encoding="utf-8")

    assert "Bootstrap policy version: `2.3`" in continuation
    assert ".terminus/agents/ACTIVE_TURN_AUTONOMY.md" in continuation
    assert "immediately re-run/reconstruct `controller_cli continue`" in continuation
    assert "`RUN_TO_BLOCKER` is mandatory" in continuation

    assert ".terminus/agents/ACTIVE_TURN_AUTONOMY.md" in agent
    assert "The default active-turn policy is `RUN_TO_BLOCKER`" in agent
    assert "Do not finish the user-visible response merely because one stage completed" in agent
    assert "never voluntarily use interruption as a lifecycle checkpoint" in agent
    assert "STOP_REASON" in agent
