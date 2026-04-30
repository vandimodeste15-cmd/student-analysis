"""
Dashboard blueprint — runs ML analysis and renders charts.
"""

import io
import csv
import logging
from flask import Blueprint, render_template, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from models import StudentEntry
from analysis.ml_engine import run_full_analysis

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def overview():
    """Main dashboard: fetch all entries, run analysis, display charts."""
    try:
        entries = StudentEntry.query.order_by(StudentEntry.created_at.desc()).all()
        analysis = run_full_analysis(entries)

        # My submissions
        my_entries = (StudentEntry.query
                      .filter_by(user_id=current_user.id)
                      .order_by(StudentEntry.created_at.desc())
                      .limit(10)
                      .all())

        return render_template(
            "dashboard/overview.html",
            analysis=analysis,
            my_entries=my_entries,
            total=len(entries),
        )
    except Exception as exc:
        logger.error("Dashboard error: %s", exc)
        flash("An error occurred while loading the dashboard.", "danger")
        return redirect(url_for("main.index"))


@dashboard_bp.route("/my-data")
@login_required
def my_data():
    """User's own submission history."""
    entries = (StudentEntry.query
               .filter_by(user_id=current_user.id)
               .order_by(StudentEntry.created_at.desc())
               .all())
    return render_template("dashboard/my_data.html", entries=entries)


@dashboard_bp.route("/export-csv")
@login_required
def export_csv():
    """Export current user's data as a CSV file."""
    try:
        entries = StudentEntry.query.filter_by(user_id=current_user.id).all()

        def generate():
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "ID", "Name", "Study Hours", "Sleep Hours",
                "Social Media Hours", "Attendance %", "Previous Grade",
                "Predicted Grade", "Performance Label", "Cluster", "Submitted At"
            ])
            for e in entries:
                writer.writerow([
                    e.id, e.name or "Anonymous",
                    e.study_hours, e.sleep_hours, e.social_media_hours,
                    e.attendance_rate, e.previous_grade,
                    e.predicted_grade or "", e.performance_label or "",
                    e.cluster_id if e.cluster_id is not None else "",
                    e.created_at.strftime("%Y-%m-%d %H:%M"),
                ])
                yield output.getvalue()
                output.truncate(0)
                output.seek(0)

        return Response(
            generate(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=my_student_data.csv"},
        )
    except Exception as exc:
        logger.error("CSV export error: %s", exc)
        flash("CSV export failed.", "danger")
        return redirect(url_for("dashboard.my_data"))
