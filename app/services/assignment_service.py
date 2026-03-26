from datetime import datetime, timedelta

from app.models import Discipline, DisciplineMembership, QuestionTicket
from app.utils.time import utcnow


URGENT_WEIGHT = {
    "baixa": 1,
    "media": 3,
    "alta": 6,
    "critica": 10,
}


def calculate_priority(ticket):
    score = URGENT_WEIGHT.get(ticket.urgency, 3)

    if ticket.deadline:
        hours_to_deadline = max((ticket.deadline - utcnow()).total_seconds() / 3600, 0)
        if hours_to_deadline <= 24:
            score += 8
        elif hours_to_deadline <= 72:
            score += 5
        elif hours_to_deadline <= 168:
            score += 2

    unresolved_count = (
        QuestionTicket.query.filter(
            QuestionTicket.student_id == ticket.student_id,
            QuestionTicket.status.in_(
                ["aberta", "triada_ia", "aguardando_monitor", "em_atendimento", "respondida"]
            ),
        ).count()
    )
    score += min(unresolved_count * 2, 6)

    if ticket.question_type in {"prova", "trabalho"}:
        score += 2
    if ticket.ai_confidence and ticket.ai_confidence < 0.55:
        score += 3

    score += min(ticket.risk_score, 6)
    ticket.priority_score = score
    return score


def suggest_monitor(ticket):
    memberships = DisciplineMembership.query.filter_by(
        discipline_id=ticket.discipline_id,
        relationship_type="monitor",
    ).all()

    if not memberships:
        return None

    candidates = []
    now = utcnow()
    for membership in memberships:
        monitor = membership.user
        open_assigned = len(
            [
                assigned
                for assigned in monitor.assigned_tickets
                if assigned.status
                in {"aguardando_monitor", "em_atendimento", "respondida", "triada_ia"}
            ]
        )
        upcoming_shift_bonus = len(
            [
                shift
                for shift in monitor.monitor_shifts
                if shift.discipline_id == ticket.discipline_id
                and now <= shift.start_at <= now + timedelta(days=7)
            ]
        )
        score = (open_assigned * 3) - upcoming_shift_bonus
        if membership.class_group_id and ticket.class_group_id == membership.class_group_id:
            score -= 2
        candidates.append((score, monitor))

    candidates.sort(key=lambda pair: (pair[0], pair[1].full_name.lower()))
    return candidates[0][1] if candidates else None


def build_prioritized_queue(user=None, course_id=None, discipline_id=None, topic_id=None, status=None):
    query = QuestionTicket.query.filter(
        QuestionTicket.status.in_(
            ["triada_ia", "aguardando_monitor", "em_atendimento", "respondida", "parcialmente_resolvida"]
        )
    )

    if course_id:
        query = query.filter(QuestionTicket.discipline.has(Discipline.course_id == course_id))
    if discipline_id:
        query = query.filter_by(discipline_id=discipline_id)
    if topic_id:
        query = query.filter_by(topic_id=topic_id)
    if status:
        query = query.filter_by(status=status)

    tickets = query.all()

    if user and user.role == "monitor":
        allowed_disciplines = {
            membership.discipline_id
            for membership in user.memberships
            if membership.relationship_type == "monitor"
        }
        allowed_courses = {
            membership.discipline.course_id
            for membership in user.memberships
            if membership.relationship_type == "monitor"
        }
        tickets = [
            ticket
            for ticket in tickets
            if ticket.discipline_id in allowed_disciplines
            and ticket.course
            and ticket.course.id in allowed_courses
        ]

    def deadline_key(ticket):
        return ticket.deadline or datetime.max

    return sorted(
        tickets,
        key=lambda item: (-item.priority_score, deadline_key(item), item.created_at),
    )
