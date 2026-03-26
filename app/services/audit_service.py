from app.extensions import db
from app.models import AuditLog


def log_action(actor, action, entity_type, entity_id, details=None):
    db.session.add(
        AuditLog(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details=details,
        )
    )
