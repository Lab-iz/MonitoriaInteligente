from pathlib import Path

from flask import Flask, redirect, url_for
from flask_login import current_user
from sqlalchemy import inspect, text

from config import config_by_name
from app.extensions import db, login_manager
from app.utils.constants import (
    INTERVENTION_TYPES,
    QUESTION_TYPES,
    TICKET_STATUSES,
    URGENCY_LEVELS,
    USER_ROLES,
    label_from,
)


def create_app(config_name="default"):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["REPORT_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    register_blueprints(app)
    register_cli(app)
    register_context_processors(app)
    register_error_handlers(app)
    ensure_existing_schema(app)

    return app


def ensure_existing_schema(app):
    """Apply tiny compatibility upgrades for the local SQLite database."""
    if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///"):
        return

    with app.app_context():
        inspector = inspect(db.engine)
        table_names = set(inspector.get_table_names())
        if "users" not in table_names:
            return

        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "phone" not in user_columns:
            db.session.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(30)"))
            db.session.commit()

        from app.models import MonitorTopic

        MonitorTopic.__table__.create(bind=db.engine, checkfirst=True)


def register_blueprints(app):
    from app.admin.routes import admin_bp
    from app.auth.routes import auth_bp
    from app.knowledge_base.routes import knowledge_bp
    from app.main.routes import main_bp
    from app.monitor.routes import monitor_bp
    from app.reports.routes import reports_bp
    from app.shifts.routes import shifts_bp
    from app.student.routes import student_bp
    from app.teacher.routes import teacher_bp
    from app.tickets.routes import tickets_bp

    blueprints = [
        auth_bp,
        main_bp,
        student_bp,
        monitor_bp,
        teacher_bp,
        admin_bp,
        tickets_bp,
        knowledge_bp,
        shifts_bp,
        reports_bp,
    ]

    for blueprint in blueprints:
        app.register_blueprint(blueprint)


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        db.drop_all()
        db.create_all()
        print("Banco inicializado.")

    @app.cli.command("seed-db")
    def seed_db():
        from app.services.seed_service import seed_demo_data

        db.create_all()
        seed_demo_data()
        print("Base populada com dados de demonstração.")


def register_context_processors(app):
    @app.context_processor
    def inject_globals():
        return {
            "user_roles": USER_ROLES,
            "question_types": QUESTION_TYPES,
            "urgency_levels": URGENCY_LEVELS,
            "ticket_statuses": TICKET_STATUSES,
            "intervention_types": INTERVENTION_TYPES,
            "label_from": label_from,
        }


def register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(_error):
        return (
            redirect(url_for(current_user.dashboard_endpoint))
            if current_user.is_authenticated
            else redirect(url_for("auth.login"))
        )
