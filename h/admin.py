"""
Admin blueprint — restricted to users with is_admin=True.
"""

import io
import csv
import logging
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, abort, Response, request
from flask_login import login_required, current_user
from extensions import db
from models import User, StudentEntry
from analysis.ml_engine import run_full_analysis

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    """Decorator that restricts access to admin users only."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/")
@admin_required
def panel():
    users   = User.query.order_by(User.created_at.desc()).all()
    entries = StudentEntry.query.order_by(StudentEntry.created_at.desc()).limit(50).all()
    analysis = run_full_analysis(StudentEntry.query.all())

    stats = {
        "total_users": User.query.count(),
        "total_entries": StudentEntry.query.count(),
        "admin_count": User.query.filter_by(is_admin=True).count(),
    }

    return render_template("admin/panel.html",
                           users=users, entries=entries,
                           analysis=analysis, stats=stats)


@admin_bp.route("/toggle-admin/<int:user_id>", methods=["POST"])
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot change your own admin status.", "warning")
    else:
        user.is_admin = not user.is_admin
        db.session.commit()
        status = "Admin" if user.is_admin else "Regular User"
        flash(f"{user.username} is now a {status}.", "success")
    return redirect(url_for("admin.panel"))


@admin_bp.route("/delete-entry/<int:entry_id>", methods=["POST"])
@admin_required
def delete_entry(entry_id):
    entry = StudentEntry.query.get_or_404(entry_id)
    try:
        db.session.delete(entry)
        db.session.commit()
        flash("Entry deleted.", "success")
    except Exception as exc:
        db.session.rollback()
        logger.error("Delete entry error: %s", exc)
        flash("Failed to delete entry.", "danger")
    return redirect(url_for("admin.panel"))


@admin_bp.route("/export-all-csv")
@admin_required
def export_all_csv():
    """Export ALL entries as CSV."""
    entries = StudentEntry.query.order_by(StudentEntry.created_at).all()

    def generate():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "User ID", "Name", "Study Hours", "Sleep Hours",
            "Social Media Hours", "Attendance %", "Previous Grade",
            "Predicted Grade", "Performance Label", "Cluster", "Submitted At"
        ])
        for e in entries:
            writer.writerow([
                e.id, e.user_id or "", e.name or "Anonymous",
                e.study_hours, e.sleep_hours, e.social_media_hours,
                e.attendance_rate, e.previous_grade,
                round(e.predicted_grade, 2) if e.predicted_grade else "",
                e.performance_label or "",
                e.cluster_id if e.cluster_id is not None else "",
                e.created_at.strftime("%Y-%m-%d %H:%M"),
            ])
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=all_student_data.csv"},
    )
