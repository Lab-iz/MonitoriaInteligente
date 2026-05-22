from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import ClassGroup, Discipline, DisciplineMembership, MonitorTopic, Topic, User
from app.utils.time import utcnow


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _registration_context():
    return {
        "class_groups": ClassGroup.query.order_by(ClassGroup.name).all(),
        "disciplines": Discipline.query.order_by(Discipline.name).all(),
        "topics": Topic.query.join(Discipline).order_by(Discipline.name, Topic.name).all(),
    }


def _selected_ids(field_name):
    ids = []
    for raw_value in request.form.getlist(field_name):
        if raw_value and raw_value.isdigit():
            ids.append(int(raw_value))
    return list(dict.fromkeys(ids))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(current_user.dashboard_endpoint))

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            user.last_login_at = utcnow()
            db.session.commit()
            login_user(user, remember=True)
            flash("Acesso realizado com sucesso.", "success")
            return redirect(url_for(user.dashboard_endpoint))

        flash("Usuário ou senha inválidos.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for(current_user.dashboard_endpoint))

    context = _registration_context()
    if request.method == "POST":
        if User.query.filter_by(username=request.form["username"].strip()).first():
            flash("Nome de usuário já cadastrado.", "danger")
            return render_template("auth/register.html", **context)

        if User.query.filter_by(email=request.form["email"].strip()).first():
            flash("E-mail já cadastrado.", "danger")
            return render_template("auth/register.html", **context)

        role = request.form["role"]
        topic_ids = _selected_ids("topic_ids")
        discipline_ids = _selected_ids("discipline_ids")
        phone = request.form.get("phone", "").strip()

        if role == "monitor" and not phone:
            flash("Informe um telefone de contato para o monitor.", "danger")
            return render_template("auth/register.html", **context)

        if role == "monitor" and not topic_ids:
            flash("Selecione ao menos um assunto que o monitor pode atender.", "danger")
            return render_template("auth/register.html", **context)

        if role == "teacher" and not discipline_ids:
            flash("Selecione ao menos uma disciplina vinculada ao professor.", "danger")
            return render_template("auth/register.html", **context)

        selected_topics = []
        selected_disciplines = []
        if role == "monitor":
            selected_topics = Topic.query.filter(Topic.id.in_(topic_ids)).all()
            if len(selected_topics) != len(topic_ids):
                flash("Selecione assuntos de monitoria válidos.", "danger")
                return render_template("auth/register.html", **context)
        elif role == "teacher":
            selected_disciplines = Discipline.query.filter(Discipline.id.in_(discipline_ids)).all()
            if len(selected_disciplines) != len(discipline_ids):
                flash("Selecione disciplinas válidas para o professor.", "danger")
                return render_template("auth/register.html", **context)

        user = User(
            full_name=request.form["full_name"].strip(),
            username=request.form["username"].strip(),
            email=request.form["email"].strip(),
            role=role,
            phone=phone or None,
        )
        user.set_password(request.form["password"])
        db.session.add(user)
        db.session.flush()

        class_group_id = request.form.get("class_group_id")
        if user.role == "student" and class_group_id:
            class_group = db.session.get(ClassGroup, int(class_group_id))
            if class_group:
                for discipline in class_group.course.disciplines:
                    db.session.add(
                        DisciplineMembership(
                            user=user,
                            discipline=discipline,
                            class_group=class_group,
                            relationship_type="student",
                        )
                    )

        elif user.role == "monitor":
            discipline_ids = sorted({topic.discipline_id for topic in selected_topics})
            for discipline_id in discipline_ids:
                db.session.add(
                    DisciplineMembership(
                        user=user,
                        discipline_id=discipline_id,
                        relationship_type="monitor",
                    )
                )
            for topic in selected_topics:
                db.session.add(MonitorTopic(monitor=user, topic=topic))

        elif user.role == "teacher":
            for discipline in selected_disciplines:
                db.session.add(
                    DisciplineMembership(
                        user=user,
                        discipline=discipline,
                        relationship_type="teacher",
                    )
                )

        db.session.commit()
        login_user(user)
        flash("Cadastro concluído. Seu ambiente institucional já está disponível.", "success")
        return redirect(url_for(user.dashboard_endpoint))

    return render_template("auth/register.html", **context)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sessão encerrada.", "info")
    return redirect(url_for("main.index"))
