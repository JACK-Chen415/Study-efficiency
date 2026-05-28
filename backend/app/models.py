from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    nickname = Column(String(50), nullable=False, unique=True, index=True)
    grade = Column(String(20), nullable=True)
    major = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow_naive)

    study_sessions = relationship("StudySession", back_populates="user")


class StudySession(Base):
    __tablename__ = "study_sessions"

    id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    user_id = Column(ID_TYPE, ForeignKey("users.id"), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    abandoned_at = Column(DateTime, nullable=True)
    abandon_reason = Column(String(100), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    time_period = Column(String(20), nullable=True)
    location = Column(String(30), nullable=True)
    task_type = Column(String(40), nullable=True)
    goal_clarity = Column(Integer, nullable=True)
    light_level = Column(Integer, nullable=True)
    noise_level = Column(Integer, nullable=True)
    fatigue_level = Column(Integer, nullable=True)
    mood_stress = Column(Integer, nullable=True)
    phone_distraction = Column(Integer, nullable=True)
    efficiency_score = Column(Integer, nullable=True)
    efficiency_label = Column(String(10), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow_naive)

    user = relationship("User", back_populates="study_sessions")
    motion_features = relationship(
        "MotionFeature",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )
    predictions = relationship(
        "Prediction",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="desc(Prediction.created_at)",
    )

    __table_args__ = (
        CheckConstraint("duration_minutes IS NULL OR duration_minutes >= 1"),
        CheckConstraint("goal_clarity IS NULL OR goal_clarity BETWEEN 1 AND 5"),
        CheckConstraint("light_level IS NULL OR light_level BETWEEN 1 AND 5"),
        CheckConstraint("noise_level IS NULL OR noise_level BETWEEN 1 AND 5"),
        CheckConstraint("fatigue_level IS NULL OR fatigue_level BETWEEN 1 AND 5"),
        CheckConstraint("mood_stress IS NULL OR mood_stress BETWEEN 1 AND 5"),
        CheckConstraint("phone_distraction IS NULL OR phone_distraction BETWEEN 1 AND 5"),
        CheckConstraint("efficiency_score IS NULL OR efficiency_score BETWEEN 1 AND 5"),
        Index("ix_study_sessions_user_start", "user_id", "start_time"),
    )


class MotionFeature(Base):
    __tablename__ = "motion_features"

    id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    session_id = Column(ID_TYPE, ForeignKey("study_sessions.id"), nullable=False, unique=True, index=True)
    move_count = Column(Integer, nullable=True)
    shake_count = Column(Integer, nullable=True)
    still_ratio = Column(Numeric(5, 4), nullable=True)
    avg_acceleration = Column(Numeric(10, 4), nullable=True)
    max_acceleration = Column(Numeric(10, 4), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow_naive)

    session = relationship("StudySession", back_populates="motion_features")

    __table_args__ = (
        CheckConstraint("move_count IS NULL OR move_count >= 0"),
        CheckConstraint("shake_count IS NULL OR shake_count >= 0"),
        CheckConstraint("still_ratio IS NULL OR still_ratio BETWEEN 0 AND 1"),
        CheckConstraint("avg_acceleration IS NULL OR avg_acceleration >= 0"),
        CheckConstraint("max_acceleration IS NULL OR max_acceleration >= 0"),
    )


class DeletedStudySession(Base):
    __tablename__ = "deleted_study_sessions"

    id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    original_session_id = Column(ID_TYPE, nullable=False, index=True)
    user_id = Column(ID_TYPE, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    time_period = Column(String(20), nullable=True)
    location = Column(String(30), nullable=True)
    task_type = Column(String(40), nullable=True)
    goal_clarity = Column(Integer, nullable=True)
    light_level = Column(Integer, nullable=True)
    noise_level = Column(Integer, nullable=True)
    fatigue_level = Column(Integer, nullable=True)
    mood_stress = Column(Integer, nullable=True)
    phone_distraction = Column(Integer, nullable=True)
    efficiency_score = Column(Integer, nullable=True)
    efficiency_label = Column(String(10), nullable=True)
    session_created_at = Column(DateTime, nullable=False)
    motion_available = Column(Integer, nullable=False, default=0)
    move_count = Column(Integer, nullable=True)
    shake_count = Column(Integer, nullable=True)
    still_ratio = Column(Numeric(5, 4), nullable=True)
    avg_acceleration = Column(Numeric(10, 4), nullable=True)
    max_acceleration = Column(Numeric(10, 4), nullable=True)
    deleted_at = Column(DateTime, nullable=False, default=utcnow_naive, index=True)
    delete_source = Column(String(40), nullable=False, default="user_history")

    __table_args__ = (
        CheckConstraint("motion_available IN (0, 1)"),
        Index("ix_deleted_sessions_user_deleted", "user_id", "deleted_at"),
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    session_id = Column(ID_TYPE, ForeignKey("study_sessions.id"), nullable=False, index=True)
    predicted_label = Column(String(10), nullable=False)
    confidence = Column(Numeric(5, 4), nullable=False)
    model_version = Column(String(80), nullable=False)
    suggestion = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow_naive)

    session = relationship("StudySession", back_populates="predictions")

    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 1"),
        Index("ix_predictions_session_created", "session_id", "created_at"),
    )
