from datetime import datetime
import math

from sqlalchemy.orm import Session

from . import models, schemas


def schema_dump(schema, **kwargs) -> dict:
    if hasattr(schema, "model_dump"):
        return schema.model_dump(**kwargs)
    return schema.dict(**kwargs)


def normalize_datetime(value: datetime | None) -> datetime:
    value = value or datetime.now()
    if value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


def get_time_period(start_time: datetime) -> str:
    hour = start_time.hour
    if 5 <= hour <= 11:
        return "morning"
    if 12 <= hour <= 17:
        return "afternoon"
    if 18 <= hour <= 22:
        return "evening"
    return "late_night"


def get_efficiency_label(score: int) -> str:
    if score <= 2:
        return "low"
    if score == 3:
        return "medium"
    return "high"


def derive_status(session: models.StudySession) -> str:
    if session.end_time is not None:
        return "completed"
    if session.abandoned_at is not None:
        return "abandoned"
    return "in_progress"


def to_session_response(session: models.StudySession) -> dict:
    return {
        "id": session.id,
        "user_id": session.user_id,
        "start_time": session.start_time,
        "end_time": session.end_time,
        "abandoned_at": session.abandoned_at,
        "abandon_reason": session.abandon_reason,
        "duration_minutes": session.duration_minutes,
        "time_period": session.time_period,
        "location": session.location,
        "task_type": session.task_type,
        "goal_clarity": session.goal_clarity,
        "light_level": session.light_level,
        "noise_level": session.noise_level,
        "fatigue_level": session.fatigue_level,
        "mood_stress": session.mood_stress,
        "phone_distraction": session.phone_distraction,
        "efficiency_score": session.efficiency_score,
        "efficiency_label": session.efficiency_label,
        "status": derive_status(session),
    }


def to_session_detail_response(session: models.StudySession) -> dict:
    latest_prediction = None
    if session.predictions:
        latest_prediction = session.predictions[0]
    return {
        **to_session_response(session),
        "motion_features": session.motion_features,
        "latest_prediction": latest_prediction,
    }


def to_delete_response(archive: models.DeletedStudySession) -> dict:
    return {
        "deleted_session_id": archive.original_session_id,
        "archived_id": archive.id,
        "deleted_at": archive.deleted_at,
        "message": "session archived and deleted",
    }


def get_user(db: Session, user_id: int) -> models.User | None:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_nickname(db: Session, nickname: str) -> models.User | None:
    return db.query(models.User).filter(models.User.nickname == nickname).first()


def simple_login(db: Session, payload: schemas.UserSimpleLoginRequest) -> tuple[models.User, bool]:
    existing = get_user_by_nickname(db, payload.nickname)
    if existing:
        return existing, False

    user = models.User(nickname=payload.nickname, grade=payload.grade, major=payload.major)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, True


def get_open_session(db: Session, user_id: int) -> models.StudySession | None:
    return (
        db.query(models.StudySession)
        .filter(
            models.StudySession.user_id == user_id,
            models.StudySession.end_time.is_(None),
            models.StudySession.abandoned_at.is_(None),
        )
        .first()
    )


def create_session(db: Session, user_id: int, start_time: datetime | None) -> models.StudySession:
    session = models.StudySession(user_id=user_id, start_time=normalize_datetime(start_time))
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: int) -> models.StudySession | None:
    return db.query(models.StudySession).filter(models.StudySession.id == session_id).first()


def abandon_session(
    db: Session,
    session: models.StudySession,
    payload: schemas.SessionAbandonRequest,
) -> models.StudySession:
    if session.abandoned_at is None:
        session.abandoned_at = models.utcnow_naive()
        session.abandon_reason = payload.reason
        db.commit()
        db.refresh(session)
    return session


def archive_and_delete_session(db: Session, session: models.StudySession) -> models.DeletedStudySession:
    motion = session.motion_features
    archive = models.DeletedStudySession(
        original_session_id=session.id,
        user_id=session.user_id,
        start_time=session.start_time,
        end_time=session.end_time,
        duration_minutes=session.duration_minutes,
        time_period=session.time_period,
        location=session.location,
        task_type=session.task_type,
        goal_clarity=session.goal_clarity,
        light_level=session.light_level,
        noise_level=session.noise_level,
        fatigue_level=session.fatigue_level,
        mood_stress=session.mood_stress,
        phone_distraction=session.phone_distraction,
        efficiency_score=session.efficiency_score,
        efficiency_label=session.efficiency_label,
        session_created_at=session.created_at,
        motion_available=1 if motion else 0,
        move_count=motion.move_count if motion else None,
        shake_count=motion.shake_count if motion else None,
        still_ratio=motion.still_ratio if motion else None,
        avg_acceleration=motion.avg_acceleration if motion else None,
        max_acceleration=motion.max_acceleration if motion else None,
    )
    db.add(archive)
    db.delete(session)
    db.commit()
    db.refresh(archive)
    return archive


def update_session_report(
    db: Session,
    session: models.StudySession,
    payload: schemas.SessionUpdateRequest,
) -> models.StudySession:
    session.location = payload.location
    session.task_type = payload.task_type
    session.goal_clarity = payload.goal_clarity
    session.light_level = payload.light_level
    session.noise_level = payload.noise_level
    session.fatigue_level = payload.fatigue_level
    session.mood_stress = payload.mood_stress
    session.phone_distraction = payload.phone_distraction
    session.efficiency_score = payload.efficiency_score
    session.efficiency_label = get_efficiency_label(payload.efficiency_score)

    for prediction in list(session.predictions):
        db.delete(prediction)

    db.commit()
    db.refresh(session)
    return session


def end_session(
    db: Session,
    session: models.StudySession,
    payload: schemas.SessionEndRequest,
) -> models.StudySession:
    end_time = normalize_datetime(payload.end_time)
    if end_time < session.start_time:
        raise ValueError("end_time must be greater than or equal to start_time")

    duration_seconds = (end_time - session.start_time).total_seconds()
    duration_minutes = max(1, math.ceil(duration_seconds / 60))

    session.end_time = end_time
    session.duration_minutes = duration_minutes
    session.time_period = get_time_period(session.start_time)
    session.location = payload.location
    session.task_type = payload.task_type
    session.goal_clarity = payload.goal_clarity
    session.light_level = payload.light_level
    session.noise_level = payload.noise_level
    session.fatigue_level = payload.fatigue_level
    session.mood_stress = payload.mood_stress
    session.phone_distraction = payload.phone_distraction
    session.efficiency_score = payload.efficiency_score
    session.efficiency_label = get_efficiency_label(payload.efficiency_score)

    db.commit()
    db.refresh(session)
    return session


def list_sessions(db: Session, user_id: int, limit: int, offset: int) -> tuple[list[models.StudySession], int]:
    query = db.query(models.StudySession).filter(
        models.StudySession.user_id == user_id,
        models.StudySession.abandoned_at.is_(None),
    )
    total = query.count()
    items = query.order_by(models.StudySession.start_time.desc()).offset(offset).limit(limit).all()
    return items, total


def get_motion_feature(db: Session, session_id: int) -> models.MotionFeature | None:
    return db.query(models.MotionFeature).filter(models.MotionFeature.session_id == session_id).first()


def upsert_motion_feature(
    db: Session,
    payload: schemas.MotionFeatureUploadRequest,
) -> tuple[models.MotionFeature, bool]:
    existing = get_motion_feature(db, payload.session_id)
    data = schema_dump(payload, exclude={"session_id"})
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing, False

    motion = models.MotionFeature(session_id=payload.session_id, **data)
    db.add(motion)
    db.commit()
    db.refresh(motion)
    return motion, True
