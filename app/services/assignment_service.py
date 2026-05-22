from datetime import datetime, timedelta

from app.models import Discipline, DisciplineMembership, MonitorTopic, QuestionTicket
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
    memberships = monitor_memberships_for_ticket(ticket)
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
        topic_bonus = 1 if monitor_can_handle_topic(monitor, ticket.topic_id) else 0
        score = (open_assigned * 3) - upcoming_shift_bonus - (topic_bonus * 4)
        if membership.class_group_id and ticket.class_group_id == membership.class_group_id:
            score -= 2
        candidates.append((score, monitor))

    candidates.sort(key=lambda pair: (pair[0], pair[1].full_name.lower()))
    return candidates[0][1] if candidates else None


def monitor_can_handle_topic(monitor, topic_id):
    if not topic_id:
        return False
    return any(capability.topic_id == topic_id for capability in monitor.monitor_topics)


def monitor_topic_ids(user):
    return {capability.topic_id for capability in user.monitor_topics}


def monitor_memberships_for_ticket(ticket):
    memberships = DisciplineMembership.query.filter_by(
        discipline_id=ticket.discipline_id,
        relationship_type="monitor",
    ).all()

    topic_monitor_ids = {
        capability.monitor_id
        for capability in MonitorTopic.query.filter_by(topic_id=ticket.topic_id).all()
    }
    if topic_monitor_ids:
        memberships = [
            membership for membership in memberships if membership.user_id in topic_monitor_ids
        ]

    return sorted(memberships, key=lambda membership: membership.user.full_name.lower())


def monitor_candidates_for_ticket(ticket):
    return [membership.user for membership in monitor_memberships_for_ticket(ticket)]


def build_prioritized_queue(user=None, course_id=None, discipline_id=None, topic_id=None, status=None):
    query = QuestionTicket.query.filter(
        QuestionTicket.status.in_(
            [
                "triada_ia",
                "aguardando_monitor",
                "em_atendimento",
                "respondida",
                "parcialmente_resolvida",
                "encaminhada_professor",
            ]
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

        allowed_topic_ids = monitor_topic_ids(user)
        if allowed_topic_ids:
            tickets = [ticket for ticket in tickets if ticket.topic_id in allowed_topic_ids]

    def deadline_key(ticket):
        return ticket.deadline or datetime.max

    return sorted(
        tickets,
        key=lambda item: (-item.priority_score, deadline_key(item), item.created_at),
    )
