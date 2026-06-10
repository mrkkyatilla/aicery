
from core.domain.hitl import ApprovalDecision, HitlMode, hitl_mode_from_checkpoint


def test_hitl_mode_from_checkpoint_graph_explicit() -> None:
    assert hitl_mode_from_checkpoint({"hitl_mode": "graph"}) == HitlMode.GRAPH


def test_hitl_mode_from_checkpoint_executor() -> None:
    assert hitl_mode_from_checkpoint({"hitl_mode": "executor"}) == HitlMode.EXECUTOR


def test_hitl_mode_from_checkpoint_legacy_graph() -> None:
    assert hitl_mode_from_checkpoint({"graph": "research-chain", "thread_id": "r1"}) == HitlMode.GRAPH


def test_resume_plan_graph_approve() -> None:
    from datetime import UTC, datetime

    from core.domain.hitl import PendingApproval
    from runtime.services.hitl_coordinator import HitlCoordinator

    pending = PendingApproval(
        approval_id="a1",
        run_id="r1",
        tool_name="read_file",
        arguments={"path": "a.md"},
        checkpoint={"hitl_mode": "graph", "thread_id": "r1", "graph": "research-chain"},
        expires_at=datetime.now(UTC),
    )
    coordinator = HitlCoordinator.__new__(HitlCoordinator)
    plan = coordinator.build_resume_plan(pending, decision=ApprovalDecision.APPROVE)
    assert plan.hitl_mode == HitlMode.GRAPH
    assert plan.spawn_continuation is True
    assert plan.signal_event is False
    assert plan.resume_payload == {"decision": "approve"}


def test_resume_plan_executor_signals_event() -> None:
    from datetime import UTC, datetime

    from core.domain.hitl import PendingApproval
    from runtime.services.hitl_coordinator import HitlCoordinator

    pending = PendingApproval(
        approval_id="a1",
        run_id="r1",
        tool_name="read_file",
        arguments={},
        checkpoint={"hitl_mode": "executor", "agent_id": "research"},
        expires_at=datetime.now(UTC),
    )
    plan = HitlCoordinator.__new__(HitlCoordinator).build_resume_plan(
        pending, decision=ApprovalDecision.APPROVE
    )
    assert plan.hitl_mode == HitlMode.EXECUTOR
    assert plan.spawn_continuation is False
    assert plan.signal_event is True


def test_build_approval_chunk_includes_hitl_mode() -> None:
    from datetime import UTC, datetime

    from core.domain.hitl import PendingApproval
    from runtime.services.hitl_coordinator import HitlCoordinator

    pending = PendingApproval(
        approval_id="a1",
        run_id="r1",
        tool_name="read_file",
        arguments={"path": "x"},
        checkpoint={"hitl_mode": "graph", "interrupt_node": "executor"},
        expires_at=datetime.now(UTC),
    )
    chunk = HitlCoordinator.build_approval_chunk(pending)
    assert chunk["hitl_mode"] == "graph"
    assert chunk["interrupt_node"] == "executor"
