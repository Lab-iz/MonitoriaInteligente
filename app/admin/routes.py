from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import ClassGroup, Course, Discipline, DisciplineMembership, Topic, User
from app.services.dashboard_service import admin_dashboard_data
from app.utils.decorators import roles_required
from app.utils.time import utcnow


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@login_required
@roles_required("admin")
def dashboard():
    data = admin_dashboard_data()
    return render_template("admin/dashboard.html", data=data)


@admin_bp.route("/management", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def management():
    if request.method == "POST":
        entity_type = request.form["entity_type"]

        if entity_type == "course":
            db.session.add(
                Course(
                    code=request.form["code"].strip(),
                    name=request.form["name"].strip(),
                    description=request.form.get("description", "").strip(),
                )
            )
            flash("Curso cadastrado.", "success")

        elif entity_type == "class_group":
            db.session.add(
                ClassGroup(
                    course_id=int(request.form["course_id"]),
                    name=request.form["name"].strip(),
                    semester_label=request.form["semester_label"].strip(),
                )
            )
            flash("Turma cadastrada.", "success")

        elif entity_type == "discipline":
            db.session.add(
                Discipline(
                    course_id=int(request.form["course_id"]),
                    code=request.form["code"].strip(),
                    name=request.form["name"].strip(),
                    description=request.form.get("description", "").strip(),
                )
            )
            flash("Disciplina cadastrada.", "success")

        elif entity_type == "topic":
            db.session.add(
                Topic(
                    discipline_id=int(request.form["discipline_id"]),
                    name=request.form["name"].strip(),
                    description=request.form.get("description", "").strip(),
                    criticality=int(request.form.get("criticality") or 1),
                )
            )
            flash("Tema cadastrado.", "success")

        elif entity_type == "user":
            user = User(
                full_name=request.form["full_name"].strip(),
                username=request.form["username"].strip(),
                email=request.form["email"].strip(),
                role=request.form["role"],
                last_login_at=utcnow(),
            )
            user.set_password(request.form["password"])
            db.session.add(user)
            flash("Usuário criado.", "success")

        elif entity_type == "membership":
            db.session.add(
                DisciplineMembership(
                    user_id=int(request.form["user_id"]),
                    discipline_id=int(request.form["discipline_id"]),
                    class_group_id=int(request.form["class_group_id"]) if request.form.get("class_group_id") else None,
                    relationship_type=request.form["relationship_type"],
                )
            )
            flash("Vínculo acadêmico criado.", "success")

        db.session.commit()
        return redirect(url_for("admin.management"))

    context = {
        "courses": Course.query.order_by(Course.name).all(),
        "class_groups": ClassGroup.query.order_by(ClassGroup.name).all(),
        "disciplines": Discipline.query.order_by(Discipline.name).all(),
        "topics": Topic.query.order_by(Topic.name).all(),
        "users": User.query.order_by(User.full_name).all(),
        "memberships": DisciplineMembership.query.order_by(DisciplineMembership.created_at.desc()).all(),
    }
    return render_template("admin/management.html", **context)
