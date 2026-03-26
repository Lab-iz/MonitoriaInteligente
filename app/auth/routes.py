from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import ClassGroup, DisciplineMembership, User
from app.utils.time import utcnow


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


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

    class_groups = ClassGroup.query.order_by(ClassGroup.name).all()
    if request.method == "POST":
        if User.query.filter_by(username=request.form["username"].strip()).first():
            flash("Nome de usuário já cadastrado.", "danger")
            return render_template("auth/register.html", class_groups=class_groups)

        if User.query.filter_by(email=request.form["email"].strip()).first():
            flash("E-mail já cadastrado.", "danger")
            return render_template("auth/register.html", class_groups=class_groups)

        user = User(
            full_name=request.form["full_name"].strip(),
            username=request.form["username"].strip(),
            email=request.form["email"].strip(),
            role=request.form["role"],
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

        db.session.commit()
        login_user(user)
        flash("Cadastro concluído. Seu ambiente institucional já está disponível.", "success")
        return redirect(url_for(user.dashboard_endpoint))

    return render_template("auth/register.html", class_groups=class_groups)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sessão encerrada.", "info")
    return redirect(url_for("main.index"))
