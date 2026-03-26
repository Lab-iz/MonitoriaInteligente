from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import ClassGroup, Discipline, MonitorShift, QuestionTicket, User
from app.services.ticket_service import attach_shift
from app.utils.decorators import roles_required


shifts_bp = Blueprint("shifts", __name__, url_prefix="/shifts")


@shifts_bp.route("/")
@login_required
def index():
    query = MonitorShift.query.order_by(MonitorShift.start_at.asc())

    if current_user.role == "monitor":
        query = query.filter_by(monitor_id=current_user.id)
    elif current_user.role == "student":
        discipline_ids = [
            membership.discipline_id
            for membership in current_user.memberships
            if membership.relationship_type == "student"
        ]
        query = query.filter(MonitorShift.discipline_id.in_(discipline_ids or [-1]))

    shifts = query.all()
    return render_template("shifts/index.html", shifts=shifts)


@shifts_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("monitor", "admin")
def create():
    if request.method == "POST":
        shift = MonitorShift(
            monitor_id=current_user.id if current_user.role == "monitor" else int(request.form["monitor_id"]),
            discipline_id=int(request.form["discipline_id"]),
            class_group_id=int(request.form["class_group_id"]) if request.form.get("class_group_id") else None,
            title=request.form["title"].strip(),
            start_at=datetime.strptime(request.form["start_at"], "%Y-%m-%dT%H:%M"),
            end_at=datetime.strptime(request.form["end_at"], "%Y-%m-%dT%H:%M"),
            location=request.form.get("location", "").strip(),
            notes=request.form.get("notes", "").strip(),
            capacity=int(request.form.get("capacity") or 10),
        )
        db.session.add(shift)
        db.session.commit()
        flash("Plantão cadastrado.", "success")
        return redirect(url_for("shifts.index"))

    return render_template(
        "shifts/new.html",
        disciplines=Discipline.query.order_by(Discipline.name).all(),
        class_groups=ClassGroup.query.order_by(ClassGroup.name).all(),
        monitors=User.query.filter_by(role="monitor").order_by(User.full_name).all(),
    )


@shifts_bp.route("/link-ticket", methods=["POST"])
@login_required
@roles_required("monitor", "admin")
def link_ticket():
    shift = db.session.get(MonitorShift, int(request.form["shift_id"]))
    ticket = db.session.get(QuestionTicket, int(request.form["ticket_id"]))
    if shift and ticket:
        attach_shift(ticket, shift)
        flash("Dúvida vinculada ao plantão.", "success")
    return redirect(url_for("tickets.ticket_detail", ticket_id=request.form["ticket_id"]))
