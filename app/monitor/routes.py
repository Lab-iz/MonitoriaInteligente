from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.services.dashboard_service import monitor_dashboard_data
from app.utils.decorators import roles_required


monitor_bp = Blueprint("monitor", __name__, url_prefix="/monitor")


@monitor_bp.route("/dashboard")
@login_required
@roles_required("monitor")
def dashboard():
    data = monitor_dashboard_data(current_user)
    return render_template("monitor/dashboard.html", data=data)
