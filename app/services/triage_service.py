from flask import current_app

from app.extensions import db
from app.models import AIResponseSuggestion
from app.services.ai_provider import get_ai_provider
from app.services.assignment_service import calculate_priority, suggest_monitor
from app.services.audit_service import log_action
from app.services.knowledge_service import search_related_items
from app.services.risk_alert_service import assess_ticket_risk
from app.utils.time import utcnow


TRANSPARENCY_NOTE = (
    "Conteúdo gerado automaticamente para apoio de triagem e organização do atendimento. "
    "A validação pedagógica final cabe ao monitor, professor ou equipe institucional."
)


def run_initial_triage(ticket, actor=None, commit=False):
    provider = get_ai_provider(current_app.config.get("AI_PROVIDER", "mock"))
    related_items = search_related_items(ticket=ticket)
    result = provider.generate_ticket_triage(ticket, related_items)

    if ticket.ai_suggestion:
        suggestion = ticket.ai_suggestion
    else:
        suggestion = AIResponseSuggestion(ticket=ticket)
        db.session.add(suggestion)

    suggestion.provider_name = result.provider_name
    suggestion.suggested_classification = result.classification
    suggestion.summary = result.summary
    suggestion.suggested_response = result.suggested_response
    suggestion.refinement_questions = result.refinement_questions
    suggestion.related_materials = result.related_materials
    suggestion.transparency_note = TRANSPARENCY_NOTE
    suggestion.confidence = result.confidence
    suggestion.low_confidence = result.low_confidence

    ticket.ai_confidence = result.confidence
    ticket.status = "aguardando_monitor" if result.low_confidence or ticket.urgency == "critica" else "triada_ia"
    ticket.last_status_changed_at = utcnow()

    assess_ticket_risk(ticket)
    calculate_priority(ticket)

    suggested_monitor = suggest_monitor(ticket)
    if suggested_monitor and ticket.status == "aguardando_monitor":
        ticket.assigned_monitor = suggested_monitor

    log_action(
        actor,
        "triagem_ia_executada",
        "QuestionTicket",
        ticket.id,
        f"Confiança: {result.confidence:.2f}; status: {ticket.status}",
    )

    if commit:
        db.session.commit()

    return suggestion


def request_human_escalation(ticket, actor=None, commit=False):
    ticket.status = "aguardando_monitor"
    ticket.last_status_changed_at = utcnow()

    if not ticket.assigned_monitor:
        ticket.assigned_monitor = suggest_monitor(ticket)

    calculate_priority(ticket)
    log_action(actor, "escalonamento_humano", "QuestionTicket", ticket.id, "Escalonado para monitoria.")

    if commit:
        db.session.commit()

    return ticket
