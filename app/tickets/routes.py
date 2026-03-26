from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import (
    ClassGroup,
    Course,
    Discipline,
    DisciplineMembership,
    MonitorShift,
    QuestionTicket,
    Topic,
    User,
)
from app.services.assignment_service import build_prioritized_queue
from app.services.feedback_service import save_feedback
from app.services.ticket_service import (
    create_ticket,
    register_monitor_response,
    request_human_support,
    set_ai_feedback,
)
from app.utils.decorators import roles_required


tickets_bp = Blueprint("tickets", __name__, url_prefix="/tickets")


def _user_can_access_ticket(ticket, user):
    if user.role == "admin":
        return True
    if user.role == "student":
        return ticket.student_id == user.id

    membership_roles = {
        membership.discipline_id: membership.relationship_type for membership in user.memberships
    }
    if user.role == "monitor":
        return (
            ticket.assigned_monitor_id == user.id
            or membership_roles.get(ticket.discipline_id) == "monitor"
        )
    if user.role == "teacher":
        return membership_roles.get(ticket.discipline_id) == "teacher"
    return False


@tickets_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("student")
def new_ticket():
    memberships = [
        membership for membership in current_user.memberships if membership.relationship_type == "student"
    ]
    disciplines = [membership.discipline for membership in memberships] or Discipline.query.order_by(Discipline.name).all()
    class_groups = [membership.class_group for membership in memberships if membership.class_group] or ClassGroup.query.order_by(ClassGroup.name).all()

    course_ids = sorted({discipline.course_id for discipline in disciplines}) or [course.id for course in Course.query.all()]
    courses = Course.query.filter(Course.id.in_(course_ids)).order_by(Course.name).all()
    discipline_ids = [discipline.id for discipline in disciplines] or [discipline.id for discipline in Discipline.query.all()]
    topics = Topic.query.filter(Topic.discipline_id.in_(discipline_ids)).order_by(Topic.name).all()

    if request.method == "POST":
        try:
            ticket = create_ticket(current_user, request.form, request.files.get("attachment"))
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Dúvida registrada com triagem inicial disponível.", "success")
            return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))

    return render_template(
        "tickets/new.html",
        courses=courses,
        disciplines=disciplines,
        class_groups=class_groups,
        topics=topics,
    )


@tickets_bp.route("/queue")
@login_required
@roles_required("monitor", "teacher", "admin")
def queue():
    course_id = int(request.args["course_id"]) if request.args.get("course_id") else None
    discipline_id = int(request.args["discipline_id"]) if request.args.get("discipline_id") else None
    topic_id = int(request.args["topic_id"]) if request.args.get("topic_id") else None
    status = request.args.get("status")

    tickets = build_prioritized_queue(
        user=current_user if current_user.role == "monitor" else None,
        course_id=course_id,
        discipline_id=discipline_id,
        topic_id=topic_id,
        status=status,
    )

    if current_user.role == "teacher":
        teacher_disciplines = {
            membership.discipline_id
            for membership in current_user.memberships
            if membership.relationship_type == "teacher"
        }
        tickets = [ticket for ticket in tickets if ticket.discipline_id in teacher_disciplines]

    if current_user.role in {"monitor", "teacher"}:
        relationship_type = "monitor" if current_user.role == "monitor" else "teacher"
        allowed_course_ids = sorted(
            {
                membership.discipline.course_id
                for membership in current_user.memberships
                if membership.relationship_type == relationship_type
            }
        )
        allowed_discipline_ids = sorted(
            {
                membership.discipline_id
                for membership in current_user.memberships
                if membership.relationship_type == relationship_type
            }
        )
        courses = Course.query.filter(Course.id.in_(allowed_course_ids or [-1])).order_by(Course.name).all()
        disciplines = Discipline.query.filter(Discipline.id.in_(allowed_discipline_ids or [-1])).order_by(Discipline.name).all()
        topics = Topic.query.filter(Topic.discipline_id.in_(allowed_discipline_ids or [-1])).order_by(Topic.name).all()
    else:
        courses = Course.query.order_by(Course.name).all()
        disciplines = Discipline.query.order_by(Discipline.name).all()
        topics = Topic.query.order_by(Topic.name).all()

    return render_template(
        "tickets/queue.html",
        tickets=tickets,
        courses=courses,
        disciplines=disciplines,
        topics=topics,
        monitors=User.query.filter_by(role="monitor").order_by(User.full_name).all(),
    )


@tickets_bp.route("/<int:ticket_id>")
@login_required
def ticket_detail(ticket_id):
    ticket = db.session.get(QuestionTicket, ticket_id)
    if not ticket or not _user_can_access_ticket(ticket, current_user):
        return redirect(url_for("main.index"))

    related_shifts = (
        MonitorShift.query.filter(
            MonitorShift.discipline_id == ticket.discipline_id,
            MonitorShift.start_at >= ticket.created_at,
        )
        .order_by(MonitorShift.start_at.asc())
        .all()
    )
    possible_monitors = [
        membership.user
        for membership in DisciplineMembership.query.filter_by(
            discipline_id=ticket.discipline_id,
            relationship_type="monitor",
        ).all()
    ]

    return render_template(
        "tickets/detail.html",
        ticket=ticket,
        related_shifts=related_shifts,
        possible_monitors=possible_monitors,
    )


@tickets_bp.route("/<int:ticket_id>/ai-feedback", methods=["POST"])
@login_required
@roles_required("student")
def ai_feedback(ticket_id):
    ticket = db.session.get(QuestionTicket, ticket_id)
    if not ticket or ticket.student_id != current_user.id:
        return redirect(url_for("student.dashboard"))

    helpful = request.form.get("helpful") == "sim"
    set_ai_feedback(ticket, helpful, actor=current_user)
    flash("Percepção sobre a resposta inicial registrada.", "success")
    return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))


@tickets_bp.route("/<int:ticket_id>/request-human", methods=["POST"])
@login_required
@roles_required("student")
def request_human(ticket_id):
    ticket = db.session.get(QuestionTicket, ticket_id)
    if not ticket or ticket.student_id != current_user.id:
        return redirect(url_for("student.dashboard"))

    request_human_support(ticket, actor=current_user)
    flash("A dúvida entrou na fila humana de monitoria.", "success")
    return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))


@tickets_bp.route("/<int:ticket_id>/assign", methods=["POST"])
@login_required
@roles_required("monitor", "admin")
def assign_ticket(ticket_id):
    ticket = db.session.get(QuestionTicket, ticket_id)
    if not ticket:
        return redirect(url_for("tickets.queue"))

    monitor_id = int(request.form["monitor_id"]) if request.form.get("monitor_id") else current_user.id
    ticket.assigned_monitor_id = monitor_id
    ticket.status = "aguardando_monitor"
    db.session.commit()
    flash("Responsável pelo atendimento definido.", "success")
    return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))


@tickets_bp.route("/<int:ticket_id>/respond", methods=["POST"])
@login_required
@roles_required("monitor", "admin")
def respond(ticket_id):
    ticket = db.session.get(QuestionTicket, ticket_id)
    if not ticket or not _user_can_access_ticket(ticket, current_user):
        return redirect(url_for("tickets.queue"))

    register_monitor_response(ticket, current_user, request.form)
    flash("Atendimento registrado.", "success")
    return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))


@tickets_bp.route("/<int:ticket_id>/feedback", methods=["POST"])
@login_required
@roles_required("student")
def feedback(ticket_id):
    ticket = db.session.get(QuestionTicket, ticket_id)
    if not ticket or ticket.student_id != current_user.id:
        return redirect(url_for("student.dashboard"))

    save_feedback(ticket, current_user, request.form)
    flash("Feedback do atendimento salvo.", "success")
    return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))
