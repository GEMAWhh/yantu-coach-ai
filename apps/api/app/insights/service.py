from collections import Counter, defaultdict
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeEdge, KnowledgeNode
from app.models.mastery import MasteryEvidence, MasterySnapshot
from app.models.planning import Goal, Task, TaskResult
from app.models.wrongbook import WrongRecord
from app.schemas.insights import (
    AnalyticsErrorsResponse,
    AnalyticsGoalRiskResponse,
    AnalyticsMasteryResponse,
    AnalyticsOverviewResponse,
    AnalyticsTimeResponse,
    CountBucket,
    ErrorByKnowledgeResponse,
    GoalRiskItemResponse,
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphResponse,
    TimeBySubjectResponse,
    WeakGraphResponse,
    WeakNodeResponse,
)

WEAK_STAGE_THRESHOLD = 4


def get_full_graph(session: Session) -> GraphResponse:
    nodes = _knowledge_nodes(session)
    node_ids = {node.id for node in nodes}
    latest_snapshots = _latest_snapshots(session)
    evidence_counts = _evidence_counts(session)
    graph_nodes = [
        GraphNodeResponse(
            id=f"knowledge:{node.id}",
            object_type="knowledge_node",
            object_id=node.id,
            label=node.name,
            subject_id=node.subject_id,
            status=node.status,
            metrics={
                "latest_stage": latest_snapshots[node.id].stage
                if node.id in latest_snapshots
                else None,
                "evidence_count": evidence_counts[node.id],
                "importance": node.importance,
                "exam_frequency": node.exam_frequency,
            },
        )
        for node in nodes
    ]
    graph_edges = [
        GraphEdgeResponse(
            id=edge.id,
            source_id=f"knowledge:{edge.source_node_id}",
            target_id=f"knowledge:{edge.target_node_id}",
            relation_type=edge.relation_type,
            weight=edge.weight,
            confirmed=edge.confirmed,
        )
        for edge in session.scalars(
            select(KnowledgeEdge).where(KnowledgeEdge.is_deleted.is_(False))
        ).all()
        if edge.source_node_id in node_ids and edge.target_node_id in node_ids
    ]
    return GraphResponse(
        nodes=graph_nodes,
        edges=graph_edges,
        total_nodes=len(graph_nodes),
        total_edges=len(graph_edges),
    )


def get_weak_graph(session: Session) -> WeakGraphResponse:
    latest_snapshots = _latest_snapshots(session)
    evidence_counts = _evidence_counts(session)
    weak_items = []
    for node in _knowledge_nodes(session):
        snapshot = latest_snapshots.get(node.id)
        if snapshot is None or snapshot.stage >= WEAK_STAGE_THRESHOLD:
            continue
        weak_items.append(
            WeakNodeResponse(
                object_type="knowledge_node",
                object_id=node.id,
                label=node.name,
                subject_id=node.subject_id,
                latest_stage=snapshot.stage,
                evidence_count=evidence_counts[node.id],
                repeat_error_rate=snapshot.repeat_error_rate,
                blocking_reasons=snapshot.blocking_reasons_json,
            )
        )
    weak_items.sort(key=lambda item: (item.latest_stage, item.label))
    return WeakGraphResponse(items=weak_items, total=len(weak_items))


def get_overview(session: Session) -> AnalyticsOverviewResponse:
    goals = _goals(session)
    tasks = _tasks(session)
    task_results = list(session.scalars(select(TaskResult)).all())
    wrong_records = list(session.scalars(select(WrongRecord)).all())
    mastery_snapshots = list(session.scalars(select(MasterySnapshot)).all())
    average_goal_progress = round(sum(goal.progress for goal in goals) / len(goals)) if goals else 0
    return AnalyticsOverviewResponse(
        knowledge_nodes=len(_knowledge_nodes(session)),
        goals=len(goals),
        tasks=len(tasks),
        task_results=len(task_results),
        wrong_records=len(wrong_records),
        mastery_snapshots=len(mastery_snapshots),
        average_goal_progress=average_goal_progress,
        task_status=_buckets(task.status for task in tasks),
        goal_risk=_buckets(goal.risk_status for goal in goals),
    )


def get_time_analytics(session: Session) -> AnalyticsTimeResponse:
    tasks = {task.id: task for task in _tasks(session)}
    by_subject: dict[str, dict[str, int]] = defaultdict(
        lambda: {"estimated_minutes": 0, "actual_minutes": 0}
    )
    for task in tasks.values():
        subject_id = task.subject_id or "unassigned"
        by_subject[subject_id]["estimated_minutes"] += task.estimated_minutes
    task_results = list(session.scalars(select(TaskResult)).all())
    for result in task_results:
        result_task = tasks.get(result.task_id)
        subject_id = (
            result_task.subject_id
            if result_task is not None and result_task.subject_id
            else "unassigned"
        )
        by_subject[subject_id]["actual_minutes"] += result.actual_minutes
    by_subject_items = [
        TimeBySubjectResponse(
            subject_id=subject_id,
            estimated_minutes=values["estimated_minutes"],
            actual_minutes=values["actual_minutes"],
        )
        for subject_id, values in sorted(by_subject.items())
    ]
    return AnalyticsTimeResponse(
        estimated_minutes=sum(task.estimated_minutes for task in tasks.values()),
        actual_minutes=sum(result.actual_minutes for result in task_results),
        by_subject=by_subject_items,
    )


def get_error_analytics(session: Session) -> AnalyticsErrorsResponse:
    wrong_records = list(session.scalars(select(WrongRecord)).all())
    by_knowledge = Counter(
        record.knowledge_node_id for record in wrong_records if record.knowledge_node_id
    )
    return AnalyticsErrorsResponse(
        total_wrong_records=len(wrong_records),
        by_status=_buckets(record.current_status for record in wrong_records),
        by_knowledge_node=[
            ErrorByKnowledgeResponse(knowledge_node_id=key, count=count)
            for key, count in sorted(by_knowledge.items())
        ],
    )


def get_mastery_analytics(session: Session) -> AnalyticsMasteryResponse:
    latest_snapshots = _latest_snapshots(session)
    distribution = _buckets(str(snapshot.stage) for snapshot in latest_snapshots.values())
    weak_count = sum(
        1 for snapshot in latest_snapshots.values() if snapshot.stage < WEAK_STAGE_THRESHOLD
    )
    return AnalyticsMasteryResponse(
        latest_snapshot_count=len(latest_snapshots),
        weak_node_count=weak_count,
        stage_distribution=distribution,
    )


def get_goal_risk_analytics(session: Session) -> AnalyticsGoalRiskResponse:
    goals = _goals(session)
    risky_goals = [
        GoalRiskItemResponse(
            object_type="goal",
            object_id=goal.id,
            title=goal.title,
            level=goal.level,
            risk_status=goal.risk_status,
            status=goal.status,
            progress=goal.progress,
        )
        for goal in goals
        if goal.risk_status != "normal" or goal.status == "delayed"
    ]
    risky_goals.sort(key=lambda goal: (goal.risk_status, goal.level, goal.title))
    return AnalyticsGoalRiskResponse(
        total_goals=len(goals),
        by_risk_status=_buckets(goal.risk_status for goal in goals),
        risky_goals=risky_goals,
    )


def _knowledge_nodes(session: Session) -> list[KnowledgeNode]:
    return list(
        session.scalars(
            select(KnowledgeNode)
            .where(KnowledgeNode.is_deleted.is_(False))
            .order_by(KnowledgeNode.subject_id, KnowledgeNode.code)
        ).all()
    )


def _latest_snapshots(session: Session) -> dict[str, MasterySnapshot]:
    snapshots = list(
        session.scalars(
            select(MasterySnapshot).order_by(
                MasterySnapshot.knowledge_node_id,
                MasterySnapshot.evaluated_at.desc(),
                MasterySnapshot.id.desc(),
            )
        ).all()
    )
    latest: dict[str, MasterySnapshot] = {}
    for snapshot in snapshots:
        latest.setdefault(snapshot.knowledge_node_id, snapshot)
    return latest


def _evidence_counts(session: Session) -> Counter[str]:
    return Counter(
        evidence.knowledge_node_id
        for evidence in session.scalars(
            select(MasteryEvidence).where(MasteryEvidence.is_deleted.is_(False))
        ).all()
    )


def _goals(session: Session) -> list[Goal]:
    return list(
        session.scalars(
            select(Goal).where(Goal.is_deleted.is_(False)).order_by(Goal.level, Goal.title)
        ).all()
    )


def _tasks(session: Session) -> list[Task]:
    return list(
        session.scalars(
            select(Task).where(Task.is_deleted.is_(False)).order_by(Task.planned_date, Task.title)
        ).all()
    )


def _buckets(values: Iterable[object]) -> list[CountBucket]:
    counter = Counter(str(value) for value in values)
    return [CountBucket(key=key, count=count) for key, count in sorted(counter.items())]
