"""
Database models for the Student Performance Analyzer.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db, login_manager


# ---------------------------------------------------------------------------
# User model (authentication + admin flag)
# ---------------------------------------------------------------------------

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship: one user → many student entries
    entries = db.relationship("StudentEntry", backref="user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------------------------------------------------------------------
# Student Entry model (the main data collected from the form)
# ---------------------------------------------------------------------------

class StudentEntry(db.Model):
    __tablename__ = "student_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Form fields
    name = db.Column(db.String(100), nullable=True)          # optional
    study_hours = db.Column(db.Float, nullable=False)        # hrs/day
    sleep_hours = db.Column(db.Float, nullable=False)        # hrs/night
    social_media_hours = db.Column(db.Float, nullable=False) # hrs/day
    attendance_rate = db.Column(db.Float, nullable=False)    # 0–100 %
    previous_grade = db.Column(db.Float, nullable=False)     # 0–100

    # Computed / predicted fields (filled after ML inference)
    predicted_grade = db.Column(db.Float, nullable=True)
    performance_label = db.Column(db.String(20), nullable=True)  # High / Average / Low
    cluster_id = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name or "Anonymous",
            "study_hours": self.study_hours,
            "sleep_hours": self.sleep_hours,
            "social_media_hours": self.social_media_hours,
            "attendance_rate": self.attendance_rate,
            "previous_grade": self.previous_grade,
            "predicted_grade": round(self.predicted_grade, 2) if self.predicted_grade else None,
            "performance_label": self.performance_label,
            "cluster_id": self.cluster_id,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
        }

    def __repr__(self):
        return f"<StudentEntry id={self.id} study={self.study_hours}h>"
