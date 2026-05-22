from sqlalchemy import func

from app.extensions import db
from app.models import (
    Discipline,
    DisciplineMembership,
    HumanResponse,
    KnowledgeBaseItem,
    MonitorShift,
    QuestionTicket,
    Topic,
    User,
)
from app.services.assignment_service import build_prioritized_queue
from app.services.risk_alert_service import active_risk_alerts
from app.utils.time import utcnow


def student_dashboard_data(user):
    recent_tickets = (
        QuestionTicket.query.filter_by(student_id=user.id)
        .order_by(QuestionTicket.created_at.desc())
        .limit(6)
        .all()
    )
    open_count = (
        QuestionTicket.query.filter(
            QuestionTicket.student_id == user.id,
            QuestionTicket.status.in_(
                ["aberta", "triada_ia", "aguardando_monitor", "em_atendimento", "respondida"]
            ),
        ).count()
    )
    resolved_count = QuestionTicket.query.filter_by(student_id=user.id, status="resolvida").count()

    difficulty = (
        db.session.query(Discipline.name, func.count(QuestionTicket.id))
        .join(QuestionTicket, QuestionTicket.discipline_id == Discipline.id)
        .filter(QuestionTicket.student_id == user.id)
        .group_by(Discipline.name)
        .order_by(func.count(QuestionTicket.id).desc())
        .limit(5)
        .all()
    )

    discipline_ids = [
        membership.discipline_id
        for membership in user.memberships
        if membership.relationship_type == "student"
    ]
    upcoming_shifts = (
        MonitorShift.query.filter(
            MonitorShift.discipline_id.in_(discipline_ids or [-1]),
            MonitorShift.start_at >= utcnow(),
        )
        .order_by(MonitorShift.start_at.asc())
        .limit(5)
        .all()
    )

    return {
        "recent_tickets": recent_tickets,
        "open_count": open_count,
        "resolved_count": resolved_count,
        "difficulty": [{"label": label, "value": value} for label, value in difficulty],
        "upcoming_shifts": upcoming_shifts,
    }


def monitor_dashboard_data(user):
    queue = build_prioritized_queue(user=user)[:8]
    in_service = (
        QuestionTicket.query.filter_by(assigned_monitor_id=user.id)
        .filter(QuestionTicket.status.in_(["aguardando_monitor", "em_atendimento", "respondida"]))
        .count()
    )
    avg_duration = (
        db.session.query(func.avg(HumanResponse.duration_minutes))
        .filter(HumanResponse.responder_id == user.id)
        .scalar()
    ) or 0
    upcoming_shifts = (
        MonitorShift.query.filter(
            MonitorShift.monitor_id == user.id,
            MonitorShift.start_at >= utcnow(),
        )
        .order_by(MonitorShift.start_at.asc())
        .limit(5)
        .all()
    )
    history = (
        HumanResponse.query.filter_by(responder_id=user.id)
        .order_by(HumanResponse.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "queue": queue,
        "in_service": in_service,
        "avg_duration": round(float(avg_duration), 1),
        "upcoming_shifts": upcoming_shifts,
        "history": history,
    }


def teacher_dashboard_data(user):
    discipline_ids = [
        membership.discipline_id
        for membership in user.memberships
        if membership.relationship_type == "teacher"
    ]
    if not discipline_ids:
        discipline_ids = [-1]

    topic_counts = (
        db.session.query(Topic.name, func.count(QuestionTicket.id))
        .join(QuestionTicket, QuestionTicket.topic_id == Topic.id)
        .filter(QuestionTicket.discipline_id.in_(discipline_ids))
        .group_by(Topic.name)
        .order_by(func.count(QuestionTicket.id).desc())
        .limit(8)
        .all()
    )
    recurring_students = (
        db.session.query(User.full_name, func.count(QuestionTicket.id))
        .join(QuestionTicket, QuestionTicket.student_id == User.id)
        .filter(QuestionTicket.discipline_id.in_(discipline_ids))
        .group_by(User.full_name)
        .order_by(func.count(QuestionTicket.id).desc())
        .limit(6)
        .all()
    )
    pending_kb = (
        KnowledgeBaseItem.query.filter(
            KnowledgeBaseItem.discipline_id.in_(discipline_ids),
            KnowledgeBaseItem.validated.is_(False),
        )
        .order_by(KnowledgeBaseItem.created_at.desc())
        .limit(6)
        .all()
    )

    total = QuestionTicket.query.filter(QuestionTicket.discipline_id.in_(discipline_ids)).count()
    resolved = (
        QuestionTicket.query.filter(
            QuestionTicket.discipline_id.in_(discipline_ids),
            QuestionTicket.status == "resolvida",
        ).count()
    )

    return {
        "topic_counts": [{"label": label, "value": value} for label, value in topic_counts],
        "recurring_students": [{"label": label, "value": value} for label, value in recurring_students],
        "pending_kb": pending_kb,
        "resolution_rate": round((resolved / total) * 100, 1) if total else 0,
    }


def admin_dashboard_data():
    total_users = User.query.count()
    total_tickets = QuestionTicket.query.count()
    open_tickets = QuestionTicket.query.filter(
        QuestionTicket.status.in_(["aberta", "triada_ia", "aguardando_monitor", "em_atendimento"])
    ).count()

    first_response_tickets = QuestionTicket.query.filter(
        QuestionTicket.first_response_at.isnot(None),
        QuestionTicket.created_at.isnot(None),
    ).all()
    resolved_tickets = QuestionTicket.query.filter(
        QuestionTicket.resolved_at.isnot(None),
        QuestionTicket.created_at.isnot(None),
    ).all()

    first_response_hours = [
        (ticket.first_response_at - ticket.created_at).total_seconds() / 3600
        for ticket in first_response_tickets
    ]
    resolution_hours = [
        (ticket.resolved_at - ticket.created_at).total_seconds() / 3600
        for ticket in resolved_tickets
    ]

    discipline_load = (
        db.session.query(Discipline.name, func.count(QuestionTicket.id))
        .join(QuestionTicket, QuestionTicket.discipline_id == Discipline.id)
        .group_by(Discipline.name)
        .order_by(func.count(QuestionTicket.id).desc())
        .limit(8)
        .all()
    )

    coverage = (
        db.session.query(Discipline.name, func.count(DisciplineMembership.id))
        .join(DisciplineMembership, DisciplineMembership.discipline_id == Discipline.id)
        .filter(DisciplineMembership.relationship_type == "monitor")
        .group_by(Discipline.name)
        .all()
    )

    ai_resolved = QuestionTicket.query.filter(
        QuestionTicket.ai_helpful.is_(True),
        QuestionTicket.status.in_(["triada_ia", "respondida", "resolvida"]),
    ).count()

    return {
        "total_users": total_users,
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "avg_first_response_hours": round(sum(first_response_hours) / len(first_response_hours), 1)
        if first_response_hours
        else 0,
        "avg_resolution_hours": round(sum(resolution_hours) / len(resolution_hours), 1)
        if resolution_hours
        else 0,
        "discipline_load": [{"label": label, "value": value} for label, value in discipline_load],
        "coverage": [{"label": label, "value": value} for label, value in coverage],
        "alerts": active_risk_alerts(),
        "ai_resolved": ai_resolved,
    }
