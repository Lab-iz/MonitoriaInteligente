from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.models import Discipline, KnowledgeBaseItem, Topic
from app.utils.decorators import roles_required
from app.utils.time import utcnow


knowledge_bp = Blueprint("knowledge", __name__, url_prefix="/knowledge-base")


@knowledge_bp.route("/")
@login_required
def index():
    query = KnowledgeBaseItem.query.filter_by(active=True)
    search_term = request.args.get("q", "").strip()
    discipline_id = request.args.get("discipline_id")

    if search_term:
        query = query.filter(
            or_(
                KnowledgeBaseItem.title.ilike(f"%{search_term}%"),
                KnowledgeBaseItem.content.ilike(f"%{search_term}%"),
                KnowledgeBaseItem.tags.ilike(f"%{search_term}%"),
            )
        )
    if discipline_id:
        query = query.filter_by(discipline_id=int(discipline_id))

    items = query.order_by(KnowledgeBaseItem.validated.desc(), KnowledgeBaseItem.created_at.desc()).all()
    return render_template(
        "knowledge_base/index.html",
        items=items,
        disciplines=Discipline.query.order_by(Discipline.name).all(),
    )


@knowledge_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("monitor", "teacher", "admin")
def create():
    if request.method == "POST":
        validated = request.form.get("validated") == "on" and current_user.role in {"teacher", "admin"}
        item = KnowledgeBaseItem(
            discipline_id=int(request.form["discipline_id"]),
            topic_id=int(request.form["topic_id"]) if request.form.get("topic_id") else None,
            title=request.form["title"].strip(),
            content=request.form["content"].strip(),
            item_type=request.form["item_type"],
            link_url=request.form.get("link_url", "").strip(),
            tags=request.form.get("tags", "").strip(),
            official=request.form.get("official") == "on",
            validated=validated,
            validated_by=current_user if validated else None,
            validated_at=utcnow() if validated else None,
            suggested_by=current_user if current_user.role == "monitor" else None,
        )
        db.session.add(item)
        db.session.commit()
        flash("Item da base de conhecimento cadastrado.", "success")
        return redirect(url_for("knowledge.index"))

    return render_template(
        "knowledge_base/new.html",
        disciplines=Discipline.query.order_by(Discipline.name).all(),
        topics=Topic.query.order_by(Topic.name).all(),
    )


@knowledge_bp.route("/<int:item_id>/validate", methods=["POST"])
@login_required
@roles_required("teacher", "admin")
def validate_item(item_id):
    item = db.session.get(KnowledgeBaseItem, item_id)
    if item:
        item.validated = True
        item.validated_by = current_user
        item.validated_at = utcnow()
        db.session.commit()
        flash("Item validado com sucesso.", "success")
    return redirect(url_for("knowledge.index"))
