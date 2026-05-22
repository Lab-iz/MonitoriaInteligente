from flask import Blueprint, render_template, send_file
from flask_login import current_user, login_required

from app.models import ReportSnapshot
from app.services.reporting_service import REPORT_LABELS, generate_csv_report
from app.utils.decorators import roles_required


reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
@login_required
@roles_required("teacher", "admin")
def index():
    snapshots = ReportSnapshot.query.order_by(ReportSnapshot.created_at.desc()).limit(10).all()
    return render_template("reports/index.html", report_labels=REPORT_LABELS, snapshots=snapshots)


@reports_bp.route("/export/<report_type>")
@login_required
@roles_required("teacher", "admin")
def export(report_type):
    snapshot = generate_csv_report(report_type, current_user)
    return send_file(snapshot.csv_path, as_attachment=True, mimetype="text/csv")
