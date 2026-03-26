from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import ClassGroup, Discipline, HumanResponse, QuestionAttachment, QuestionTicket, Topic
from app.services.assignment_service import calculate_priority
from app.services.audit_service import log_action
from app.services.triage_service import request_human_escalation, run_initial_triage
from app.utils.time import utcnow


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "txt", "py", "docx"}


def _parse_datetime(raw_value):
    if not raw_value:
        return None
    return datetime.strptime(raw_value, "%Y-%m-%dT%H:%M")


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_ticket_number():
    return f"MI-{utcnow().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"


def save_attachment(ticket, upload_file):
    if not upload_file or not isinstance(upload_file, FileStorage) or not upload_file.filename:
        return None
    if not _allowed_file(upload_file.filename):
        return None

    original_name = secure_filename(upload_file.filename)
    stored_name = f"{uuid4().hex}_{original_name}"
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / stored_name
    upload_file.save(destination)

    attachment = QuestionAttachment(
        ticket=ticket,
        original_filename=original_name,
        stored_filename=stored_name,
        file_path=str(destination),
    )
    db.session.add(attachment)
    return attachment


def create_ticket(student, form_data, upload_file=None):
    course_id = int(form_data["course_id"])
    discipline = db.session.get(Discipline, int(form_data["discipline_id"]))
    topic = db.session.get(Topic, int(form_data["topic_id"]))
    class_group = (
        db.session.get(ClassGroup, int(form_data["class_group_id"]))
        if form_data.get("class_group_id")
        else None
    )

    if not discipline or discipline.course_id != course_id:
        raise ValueError("A disciplina selecionada não pertence ao curso informado.")
    if not topic or topic.discipline_id != discipline.id:
        raise ValueError("O tema selecionado não pertence à disciplina informada.")
    if class_group and class_group.course_id != course_id:
        raise ValueError("A turma selecionada não pertence ao curso informado.")

    ticket = QuestionTicket(
        ticket_number=generate_ticket_number(),
        student=student,
        discipline_id=discipline.id,
        topic_id=topic.id,
        class_group_id=class_group.id if class_group else None,
        title=form_data["title"].strip(),
        description=form_data["description"].strip(),
        question_type=form_data["question_type"],
        urgency=form_data["urgency"],
        deadline=_parse_datetime(form_data.get("deadline")),
        prior_attempt=form_data.get("prior_attempt", "").strip(),
        status="aberta",
    )
    db.session.add(ticket)
    db.session.flush()

    save_attachment(ticket, upload_file)
    run_initial_triage(ticket, actor=student)
    log_action(student, "abertura_duvida", "QuestionTicket", ticket.id, ticket.title)

    db.session.commit()
    return ticket


def set_ai_feedback(ticket, helpful, actor=None):
    ticket.ai_helpful = helpful
    calculate_priority(ticket)
    log_action(actor, "feedback_resposta_ia", "QuestionTicket", ticket.id, f"Útil: {helpful}")
    db.session.commit()
    return ticket


def request_human_support(ticket, actor=None):
    request_human_escalation(ticket, actor=actor)
    db.session.commit()
    return ticket


def register_monitor_response(ticket, responder, form_data):
    status_after = form_data["status_after"]
    response = HumanResponse(
        ticket=ticket,
        responder=responder,
        body=form_data["body"].strip(),
        intervention_type=form_data["intervention_type"],
        recommended_materials=form_data.get("recommended_materials", "").strip(),
        pedagogical_notes=form_data.get("pedagogical_notes", "").strip(),
        duration_minutes=int(form_data.get("duration_minutes") or 0),
        status_after=status_after,
    )
    db.session.add(response)

    if not ticket.first_response_at:
        ticket.first_response_at = utcnow()

    ticket.assigned_monitor = responder
    ticket.status = status_after
    ticket.last_status_changed_at = utcnow()

    if status_after in {"resolvida", "arquivada"}:
        ticket.resolved_at = utcnow()

    calculate_priority(ticket)
    log_action(responder, "resposta_monitor", "QuestionTicket", ticket.id, status_after)
    db.session.commit()
    return response


def attach_shift(ticket, shift):
    ticket.linked_shift = shift
    calculate_priority(ticket)
    db.session.commit()
    return ticket
