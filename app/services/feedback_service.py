from app.extensions import db
from app.models import ResponseFeedback
from app.services.audit_service import log_action


def save_feedback(ticket, student, form_data):
    feedback = ResponseFeedback.query.filter_by(ticket_id=ticket.id, student_id=student.id).first()
    if not feedback:
        feedback = ResponseFeedback(ticket=ticket, student=student)
        db.session.add(feedback)

    ai_helpful_raw = form_data.get("ai_helpful")
    feedback.ai_helpful = None if ai_helpful_raw is None else ai_helpful_raw == "sim"
    feedback.monitor_rating = int(form_data["monitor_rating"]) if form_data.get("monitor_rating") else None
    feedback.resolved = form_data.get("resolved") == "sim"
    feedback.comment = form_data.get("comment", "").strip()

    ticket.ai_helpful = feedback.ai_helpful
    if feedback.resolved and ticket.status not in {"resolvida", "arquivada"}:
        ticket.status = "resolvida"

    log_action(student, "feedback_atendimento", "QuestionTicket", ticket.id, feedback.comment or "Sem comentário")
    db.session.commit()
    return feedback
