"""
Main blueprint: homepage, data entry form, and prediction endpoint.
"""

import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user, login_required
from extensions import db
from models import StudentEntry
from analysis.ml_engine import multiple_linear_regression, _build_df, _label_performance

logger = logging.getLogger(__name__)
main_bp = Blueprint("main", __name__)


# ── Home ─────────────────────────────────────────────────────────────────────

@main_bp.route("/")
def index():
    total = StudentEntry.query.count()
    return render_template("index.html", total_entries=total)


# ── Data collection form ─────────────────────────────────────────────────────

@main_bp.route("/collect", methods=["GET", "POST"])
@login_required
def collect():
    if request.method == "POST":
        try:
            # ── Validation ──────────────────────────────────────────────────
            errors = []

            name = request.form.get("name", "").strip() or None

            def _float_field(field, label, lo, hi):
                raw = request.form.get(field, "").strip()
                if not raw:
                    errors.append(f"{label} is required.")
                    return None
                try:
                    val = float(raw)
                except ValueError:
                    errors.append(f"{label} must be a number.")
                    return None
                if not (lo <= val <= hi):
                    errors.append(f"{label} must be between {lo} and {hi}.")
                    return None
                return val

            study_hours        = _float_field("study_hours",        "Study hours",         0, 24)
            sleep_hours        = _float_field("sleep_hours",         "Sleep hours",          0, 24)
            social_media_hours = _float_field("social_media_hours",  "Social media hours",   0, 24)
            attendance_rate    = _float_field("attendance_rate",     "Attendance rate",      0, 100)
            previous_grade     = _float_field("previous_grade",      "Previous grade",       0, 100)

            if errors:
                for e in errors:
                    flash(e, "danger")
                return render_template("collect.html", form_data=request.form)

            # ── Sanity: hours don't exceed 24 ───────────────────────────────
            total_hours = study_hours + sleep_hours + social_media_hours
            if total_hours > 24:
                flash("Study + Sleep + Social media hours cannot exceed 24h per day.", "warning")
                return render_template("collect.html", form_data=request.form)

            # ── Build entry ─────────────────────────────────────────────────
            entry = StudentEntry(
                user_id=current_user.id,
                name=name,
                study_hours=study_hours,
                sleep_hours=sleep_hours,
                social_media_hours=social_media_hours,
                attendance_rate=attendance_rate,
                previous_grade=previous_grade,
            )

            # Immediately classify with rule-based label
            entry.performance_label = _label_performance(previous_grade)

            # Quick grade prediction if enough data exists
            all_entries = StudentEntry.query.all()
            if len(all_entries) >= 5:
                try:
                    df = _build_df(all_entries)
                    if df is not None:
                        mlr = multiple_linear_regression(df)
                        if mlr["available"]:
                            import numpy as np
                            X = np.array([[study_hours, sleep_hours,
                                           social_media_hours, attendance_rate]])
                            entry.predicted_grade = float(mlr["model"].predict(X)[0])
                except Exception as pred_err:
                    logger.warning("Prediction on submit failed: %s", pred_err)

            db.session.add(entry)
            db.session.commit()

            flash("✅ Your data has been submitted! Check the dashboard for insights.", "success")
            return redirect(url_for("dashboard.overview"))

        except Exception as exc:
            db.session.rollback()
            logger.error("Error saving entry: %s", exc)
            flash("An unexpected error occurred. Please try again.", "danger")

    return render_template("collect.html", form_data={})


# ── Live prediction (AJAX) ────────────────────────────────────────────────────

@main_bp.route("/api/predict", methods=["POST"])
@login_required
def api_predict():
    """Return a quick grade prediction based on form values (no DB write)."""
    try:
        data = request.get_json(force=True)
        study   = float(data.get("study_hours", 0))
        sleep   = float(data.get("sleep_hours", 0))
        social  = float(data.get("social_media_hours", 0))
        attend  = float(data.get("attendance_rate", 0))

        entries = StudentEntry.query.all()
        if len(entries) < 5:
            return jsonify({"error": "Not enough data yet for prediction."})

        df = _build_df(entries)
        if df is None:
            return jsonify({"error": "Not enough clean data."})

        mlr = multiple_linear_regression(df)
        if not mlr["available"]:
            return jsonify({"error": "Model not available."})

        import numpy as np
        X = np.array([[study, sleep, social, attend]])
        predicted = float(mlr["model"].predict(X)[0])
        predicted = max(0, min(100, predicted))   # clamp
        label = _label_performance(predicted)

        return jsonify({"predicted_grade": round(predicted, 1), "label": label})

    except Exception as exc:
        logger.error("Predict API error: %s", exc)
        return jsonify({"error": str(exc)}), 400
