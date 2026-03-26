from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.services.dashboard_service import student_dashboard_data
from app.utils.decorators import roles_required


student_bp = Blueprint("student", __name__, url_prefix="/student")


@student_bp.route("/dashboard")
@login_required
@roles_required("student")
def dashboard():
    data = student_dashboard_data(current_user)
    return render_template("student/dashboard.html", data=data)
