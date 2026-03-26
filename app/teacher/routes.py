from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.services.dashboard_service import teacher_dashboard_data
from app.utils.decorators import roles_required


teacher_bp = Blueprint("teacher", __name__, url_prefix="/teacher")


@teacher_bp.route("/dashboard")
@login_required
@roles_required("teacher")
def dashboard():
    data = teacher_dashboard_data(current_user)
    return render_template("teacher/dashboard.html", data=data)
