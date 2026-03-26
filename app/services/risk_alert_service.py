from app.extensions import db
from app.models import QuestionTicket, RiskAlert
from app.utils.time import utcnow


def assess_ticket_risk(ticket):
    score = 0

    unresolved_count = (
        QuestionTicket.query.filter(
            QuestionTicket.student_id == ticket.student_id,
            QuestionTicket.status.in_(
                ["aberta", "triada_ia", "aguardando_monitor", "em_atendimento", "respondida"]
            ),
        ).count()
    )
    if unresolved_count >= 3:
        score += 2

    if ticket.urgency in {"alta", "critica"}:
        score += 2
    if ticket.deadline and (ticket.deadline - utcnow()).days <= 2:
        score += 2
    if ticket.topic and ticket.topic.criticality >= 3:
        score += 1

    ticket.risk_score = score
    if score >= 4:
        level = "alto"
    elif score >= 2:
        level = "moderado"
    else:
        level = "baixo"

    if score >= 2:
        existing = RiskAlert.query.filter_by(ticket_id=ticket.id, status="ativo").first()
        reason = (
            f"Reincidência e/ou urgência detectadas para {ticket.student.full_name} "
            f"na disciplina {ticket.discipline.name}."
        )
        if existing:
            existing.level = level
            existing.reason = reason
        else:
            db.session.add(
                RiskAlert(
                    student=ticket.student,
                    discipline=ticket.discipline,
                    ticket=ticket,
                    level=level,
                    reason=reason,
                )
            )

    return level


def active_risk_alerts(limit=10):
    return (
        RiskAlert.query.filter_by(status="ativo")
        .order_by(RiskAlert.created_at.desc())
        .limit(limit)
        .all()
    )
