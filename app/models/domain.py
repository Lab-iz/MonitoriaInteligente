from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager
from app.utils.time import utcnow


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False, default="student", index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active_user = db.Column(db.Boolean, default=True, nullable=False)
    phone = db.Column(db.String(30))
    bio = db.Column(db.Text)
    last_login_at = db.Column(db.DateTime)

    memberships = db.relationship(
        "DisciplineMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    submitted_tickets = db.relationship(
        "QuestionTicket",
        back_populates="student",
        foreign_keys="QuestionTicket.student_id",
    )
    assigned_tickets = db.relationship(
        "QuestionTicket",
        back_populates="assigned_monitor",
        foreign_keys="QuestionTicket.assigned_monitor_id",
    )
    human_responses = db.relationship("HumanResponse", back_populates="responder")
    feedback_entries = db.relationship("ResponseFeedback", back_populates="student")
    validated_items = db.relationship(
        "KnowledgeBaseItem",
        back_populates="validated_by",
        foreign_keys="KnowledgeBaseItem.validated_by_id",
    )
    suggested_items = db.relationship(
        "KnowledgeBaseItem",
        back_populates="suggested_by",
        foreign_keys="KnowledgeBaseItem.suggested_by_id",
    )
    monitor_shifts = db.relationship("MonitorShift", back_populates="monitor")
    monitor_topics = db.relationship(
        "MonitorTopic",
        back_populates="monitor",
        cascade="all, delete-orphan",
    )
    alerts = db.relationship(
        "RiskAlert",
        back_populates="student",
        foreign_keys="RiskAlert.student_id",
    )
    generated_reports = db.relationship("ReportSnapshot", back_populates="generated_by")
    audit_logs = db.relationship("AuditLog", back_populates="actor")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self.is_active_user

    @property
    def dashboard_endpoint(self):
        endpoints = {
            "student": "student.dashboard",
            "monitor": "monitor.dashboard",
            "teacher": "teacher.dashboard",
            "admin": "admin.dashboard",
        }
        return endpoints.get(self.role, "main.index")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Course(TimestampMixin, db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)

    class_groups = db.relationship("ClassGroup", back_populates="course")
    disciplines = db.relationship("Discipline", back_populates="course")


class ClassGroup(TimestampMixin, db.Model):
    __tablename__ = "class_groups"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    semester_label = db.Column(db.String(40), nullable=False)

    course = db.relationship("Course", back_populates="class_groups")
    memberships = db.relationship("DisciplineMembership", back_populates="class_group")
    tickets = db.relationship("QuestionTicket", back_populates="class_group")
    shifts = db.relationship("MonitorShift", back_populates="class_group")


class Discipline(TimestampMixin, db.Model):
    __tablename__ = "disciplines"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)

    course = db.relationship("Course", back_populates="disciplines")
    topics = db.relationship("Topic", back_populates="discipline")
    memberships = db.relationship("DisciplineMembership", back_populates="discipline")
    tickets = db.relationship("QuestionTicket", back_populates="discipline")
    knowledge_items = db.relationship("KnowledgeBaseItem", back_populates="discipline")
    monitor_shifts = db.relationship("MonitorShift", back_populates="discipline")
    alerts = db.relationship("RiskAlert", back_populates="discipline")


class Topic(TimestampMixin, db.Model):
    __tablename__ = "topics"

    id = db.Column(db.Integer, primary_key=True)
    discipline_id = db.Column(db.Integer, db.ForeignKey("disciplines.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    criticality = db.Column(db.Integer, default=1, nullable=False)

    discipline = db.relationship("Discipline", back_populates="topics")
    tickets = db.relationship("QuestionTicket", back_populates="topic")
    knowledge_items = db.relationship("KnowledgeBaseItem", back_populates="topic")
    monitor_capabilities = db.relationship(
        "MonitorTopic",
        back_populates="topic",
        cascade="all, delete-orphan",
    )


class MonitorTopic(TimestampMixin, db.Model):
    __tablename__ = "monitor_topics"
    __table_args__ = (
        db.UniqueConstraint("monitor_id", "topic_id", name="uq_monitor_topic"),
    )

    id = db.Column(db.Integer, primary_key=True)
    monitor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), nullable=False)

    monitor = db.relationship("User", back_populates="monitor_topics")
    topic = db.relationship("Topic", back_populates="monitor_capabilities")


class DisciplineMembership(TimestampMixin, db.Model):
    __tablename__ = "discipline_memberships"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "discipline_id",
            "class_group_id",
            "relationship_type",
            name="uq_membership_link",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    discipline_id = db.Column(db.Integer, db.ForeignKey("disciplines.id"), nullable=False)
    class_group_id = db.Column(db.Integer, db.ForeignKey("class_groups.id"), nullable=True)
    relationship_type = db.Column(db.String(20), nullable=False)

    user = db.relationship("User", back_populates="memberships")
    discipline = db.relationship("Discipline", back_populates="memberships")
    class_group = db.relationship("ClassGroup", back_populates="memberships")


class QuestionTicket(TimestampMixin, db.Model):
    __tablename__ = "question_tickets"

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    discipline_id = db.Column(db.Integer, db.ForeignKey("disciplines.id"), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), nullable=False)
    class_group_id = db.Column(db.Integer, db.ForeignKey("class_groups.id"), nullable=True)
    assigned_monitor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    linked_shift_id = db.Column(db.Integer, db.ForeignKey("monitor_shifts.id"), nullable=True)

    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(30), nullable=False)
    urgency = db.Column(db.String(20), nullable=False, default="media")
    deadline = db.Column(db.DateTime)
    prior_attempt = db.Column(db.Text)
    status = db.Column(db.String(40), nullable=False, default="aberta", index=True)
    priority_score = db.Column(db.Integer, default=0, nullable=False, index=True)
    risk_score = db.Column(db.Integer, default=0, nullable=False)
    ai_confidence = db.Column(db.Float, default=0.0, nullable=False)
    ai_helpful = db.Column(db.Boolean)
    first_response_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    last_status_changed_at = db.Column(db.DateTime, default=utcnow)

    student = db.relationship(
        "User",
        back_populates="submitted_tickets",
        foreign_keys=[student_id],
    )
    assigned_monitor = db.relationship(
        "User",
        back_populates="assigned_tickets",
        foreign_keys=[assigned_monitor_id],
    )
    discipline = db.relationship("Discipline", back_populates="tickets")
    topic = db.relationship("Topic", back_populates="tickets")
    class_group = db.relationship("ClassGroup", back_populates="tickets")
    attachments = db.relationship(
        "QuestionAttachment",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    ai_suggestion = db.relationship(
        "AIResponseSuggestion",
        back_populates="ticket",
        uselist=False,
        cascade="all, delete-orphan",
    )
    human_responses = db.relationship(
        "HumanResponse",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="HumanResponse.created_at",
    )
    feedback_entries = db.relationship(
        "ResponseFeedback",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    linked_shift = db.relationship("MonitorShift", back_populates="linked_tickets")
    alerts = db.relationship("RiskAlert", back_populates="ticket")

    @property
    def latest_response(self):
        return self.human_responses[-1] if self.human_responses else None

    @property
    def is_open(self):
        return self.status not in {"resolvida", "arquivada"}

    @property
    def course(self):
        if self.class_group and self.class_group.course:
            return self.class_group.course
        if self.discipline and self.discipline.course:
            return self.discipline.course
        return None


class QuestionAttachment(TimestampMixin, db.Model):
    __tablename__ = "question_attachments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("question_tickets.id"), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)

    ticket = db.relationship("QuestionTicket", back_populates="attachments")


class AIResponseSuggestion(TimestampMixin, db.Model):
    __tablename__ = "ai_response_suggestions"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("question_tickets.id"), nullable=False, unique=True)
    provider_name = db.Column(db.String(80), nullable=False, default="mock")
    suggested_classification = db.Column(db.String(120), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    suggested_response = db.Column(db.Text, nullable=False)
    refinement_questions = db.Column(db.Text)
    related_materials = db.Column(db.Text)
    transparency_note = db.Column(db.Text, nullable=False)
    confidence = db.Column(db.Float, default=0.0, nullable=False)
    low_confidence = db.Column(db.Boolean, default=False, nullable=False)

    ticket = db.relationship("QuestionTicket", back_populates="ai_suggestion")


class HumanResponse(TimestampMixin, db.Model):
    __tablename__ = "human_responses"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("question_tickets.id"), nullable=False)
    responder_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    intervention_type = db.Column(db.String(40), nullable=False)
    recommended_materials = db.Column(db.Text)
    pedagogical_notes = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer, default=0, nullable=False)
    status_after = db.Column(db.String(40), nullable=False)

    ticket = db.relationship("QuestionTicket", back_populates="human_responses")
    responder = db.relationship("User", back_populates="human_responses")


class ResponseFeedback(TimestampMixin, db.Model):
    __tablename__ = "response_feedbacks"
    __table_args__ = (
        db.UniqueConstraint("ticket_id", "student_id", name="uq_feedback_ticket_student"),
    )

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("question_tickets.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    ai_helpful = db.Column(db.Boolean)
    monitor_rating = db.Column(db.Integer)
    resolved = db.Column(db.Boolean)
    comment = db.Column(db.Text)

    ticket = db.relationship("QuestionTicket", back_populates="feedback_entries")
    student = db.relationship("User", back_populates="feedback_entries")


class KnowledgeBaseItem(TimestampMixin, db.Model):
    __tablename__ = "knowledge_base_items"

    id = db.Column(db.Integer, primary_key=True)
    discipline_id = db.Column(db.Integer, db.ForeignKey("disciplines.id"), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), nullable=True)
    title = db.Column(db.String(180), nullable=False)
    content = db.Column(db.Text, nullable=False)
    item_type = db.Column(db.String(40), nullable=False)
    link_url = db.Column(db.String(255))
    tags = db.Column(db.String(255))
    official = db.Column(db.Boolean, default=False, nullable=False)
    validated = db.Column(db.Boolean, default=False, nullable=False)
    validated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    validated_at = db.Column(db.DateTime)
    suggested_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)

    discipline = db.relationship("Discipline", back_populates="knowledge_items")
    topic = db.relationship("Topic", back_populates="knowledge_items")
    validated_by = db.relationship(
        "User",
        back_populates="validated_items",
        foreign_keys=[validated_by_id],
    )
    suggested_by = db.relationship(
        "User",
        back_populates="suggested_items",
        foreign_keys=[suggested_by_id],
    )

    @property
    def tag_list(self):
        return [tag.strip() for tag in (self.tags or "").split(",") if tag.strip()]


class MonitorShift(TimestampMixin, db.Model):
    __tablename__ = "monitor_shifts"

    id = db.Column(db.Integer, primary_key=True)
    monitor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    discipline_id = db.Column(db.Integer, db.ForeignKey("disciplines.id"), nullable=False)
    class_group_id = db.Column(db.Integer, db.ForeignKey("class_groups.id"), nullable=True)
    title = db.Column(db.String(180), nullable=False)
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(180))
    notes = db.Column(db.Text)
    capacity = db.Column(db.Integer, default=10, nullable=False)
    attendance_count = db.Column(db.Integer, default=0, nullable=False)

    monitor = db.relationship("User", back_populates="monitor_shifts")
    discipline = db.relationship("Discipline", back_populates="monitor_shifts")
    class_group = db.relationship("ClassGroup", back_populates="shifts")
    linked_tickets = db.relationship("QuestionTicket", back_populates="linked_shift")


class RiskAlert(TimestampMixin, db.Model):
    __tablename__ = "risk_alerts"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    discipline_id = db.Column(db.Integer, db.ForeignKey("disciplines.id"), nullable=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("question_tickets.id"), nullable=True)
    level = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="ativo")

    student = db.relationship("User", back_populates="alerts", foreign_keys=[student_id])
    discipline = db.relationship("Discipline", back_populates="alerts")
    ticket = db.relationship("QuestionTicket", back_populates="alerts")


class ReportSnapshot(TimestampMixin, db.Model):
    __tablename__ = "report_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    report_type = db.Column(db.String(50), nullable=False)
    generated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    filters_json = db.Column(db.JSON)
    csv_path = db.Column(db.String(255), nullable=False)

    generated_by = db.relationship("User", back_populates="generated_reports")


class AuditLog(TimestampMixin, db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(120), nullable=False)
    entity_type = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.String(80), nullable=False)
    details = db.Column(db.Text)

    actor = db.relationship("User", back_populates="audit_logs")
