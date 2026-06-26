from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from . import models
from .model_service import ModelUnavailableError, load_feature_importance, load_metrics


TIME_PERIOD_ORDER = ["morning", "afternoon", "evening", "late_night"]
EFFICIENCY_LABEL_ORDER = ["low", "medium", "high"]


def completed_user_sessions(db: Session, user_id: int) -> list[models.StudySession]:
    return (
        db.query(models.StudySession)
        .filter(
            models.StudySession.user_id == user_id,
            models.StudySession.end_time.is_not(None),
            models.StudySession.abandoned_at.is_(None),
            models.StudySession.efficiency_score.is_not(None),
        )
        .order_by(models.StudySession.start_time.asc())
        .all()
    )


def latest_prediction_for_user(db: Session, user_id: int) -> models.Prediction | None:
    return (
        db.query(models.Prediction)
        .join(models.StudySession, models.StudySession.id == models.Prediction.session_id)
        .filter(
            models.StudySession.user_id == user_id,
            models.StudySession.end_time.is_not(None),
            models.StudySession.abandoned_at.is_(None),
        )
        .order_by(models.Prediction.created_at.desc(), models.Prediction.id.desc())
        .first()
    )


def round_optional(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def high_efficiency_ratio(sessions: list[models.StudySession]) -> float:
    if not sessions:
        return 0.0
    high_count = sum(1 for session in sessions if session.efficiency_label == "high")
    return round(high_count / len(sessions), 4)


def average(values: list[int | float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def aggregate_session_group(sessions: list[models.StudySession]) -> dict[str, Any]:
    durations = [session.duration_minutes or 0 for session in sessions]
    scores = [session.efficiency_score for session in sessions if session.efficiency_score is not None]
    return {
        "session_count": len(sessions),
        "duration_minutes": sum(durations),
        "avg_duration_minutes": round_optional(average(durations)),
        "avg_efficiency_score": round_optional(average(scores)),
        "high_efficiency_ratio": high_efficiency_ratio(sessions),
    }


def get_overview(db: Session, user_id: int) -> dict[str, Any]:
    sessions = completed_user_sessions(db, user_id)
    aggregate = aggregate_session_group(sessions)
    labels = {label: 0 for label in EFFICIENCY_LABEL_ORDER}
    for session in sessions:
        if session.efficiency_label in labels:
            labels[session.efficiency_label] += 1

    latest_session = sessions[-1] if sessions else None
    return {
        "user_id": user_id,
        "total_sessions": aggregate["session_count"],
        "total_duration_minutes": aggregate["duration_minutes"],
        "avg_duration_minutes": aggregate["avg_duration_minutes"],
        "avg_efficiency_score": aggregate["avg_efficiency_score"],
        "high_efficiency_ratio": aggregate["high_efficiency_ratio"],
        "label_distribution": labels,
        "motion_available_count": sum(1 for session in sessions if session.motion_features is not None),
        "latest_session_at": latest_session.start_time if latest_session else None,
        "latest_prediction": latest_prediction_for_user(db, user_id),
        "data_scope": "completed_non_abandoned_sessions",
    }


def get_trend(db: Session, user_id: int) -> dict[str, Any]:
    grouped: dict[date, list[models.StudySession]] = defaultdict(list)
    for session in completed_user_sessions(db, user_id):
        grouped[session.start_time.date()].append(session)

    items = []
    for day in sorted(grouped):
        aggregate = aggregate_session_group(grouped[day])
        items.append({"date": day.isoformat(), **aggregate})
    return {"user_id": user_id, "items": items}


def period_sort_key(period: str | None) -> int:
    if period in TIME_PERIOD_ORDER:
        return TIME_PERIOD_ORDER.index(period)
    return len(TIME_PERIOD_ORDER)


def build_time_periods(sessions: list[models.StudySession]) -> list[dict[str, Any]]:
    grouped: dict[str, list[models.StudySession]] = defaultdict(list)
    for session in sessions:
        if session.time_period in TIME_PERIOD_ORDER:
            grouped[session.time_period].append(session)

    items = []
    for period in sorted(grouped, key=period_sort_key):
        aggregate = aggregate_session_group(grouped[period])
        items.append({"time_period": period, **aggregate})
    return items


def build_motion_points(sessions: list[models.StudySession]) -> list[dict[str, Any]]:
    points = []
    for session in sessions:
        motion = session.motion_features
        if motion is None or session.efficiency_score is None or session.efficiency_label is None:
            continue
        points.append(
            {
                "session_id": session.id,
                "start_time": session.start_time,
                "move_count": motion.move_count or 0,
                "shake_count": motion.shake_count or 0,
                "still_ratio": as_float(motion.still_ratio),
                "efficiency_score": session.efficiency_score,
                "efficiency_label": session.efficiency_label,
            }
        )
    return points


def trigger_count(sessions: list[models.StudySession], predicate) -> int:
    return sum(1 for session in sessions if predicate(session))


def build_rule_suggestions(sessions: list[models.StudySession]) -> list[dict[str, Any]]:
    rules = [
        (
            "high_fatigue",
            "高疲劳建议",
            "疲劳评分达到 4 或 5 的记录较多时，建议把学习拆成更短轮次，并在开始前安排休息。",
            lambda session: session.fatigue_level is not None and session.fatigue_level >= 4,
        ),
        (
            "phone_distraction",
            "强手机干扰建议",
            "手机干扰达到 4 或 5 时，建议开启勿扰模式、移出视线范围，并用固定时间点集中查看消息。",
            lambda session: session.phone_distraction is not None and session.phone_distraction >= 4,
        ),
        (
            "low_goal_clarity",
            "目标清晰度低建议",
            "目标清晰度为 1 或 2 时，建议先写下本轮任务、完成标准和预计时长，再开始计时。",
            lambda session: session.goal_clarity is not None and session.goal_clarity <= 2,
        ),
        (
            "high_noise",
            "噪声高建议",
            "噪声评分达到 4 或 5 时，建议优先选择图书馆、自习室或使用降噪耳机。",
            lambda session: session.noise_level is not None and session.noise_level >= 4,
        ),
        (
            "late_night",
            "深夜学习建议",
            "深夜学习记录较多时，建议控制单次时长，并把高认知负荷任务尽量前移。",
            lambda session: session.time_period == "late_night",
        ),
    ]
    items = []
    for code, title, message, predicate in rules:
        count = trigger_count(sessions, predicate)
        items.append(
            {
                "code": code,
                "title": title,
                "message": message,
                "trigger_count": count,
                "active": count > 0,
            }
        )
    return items


def load_model_snapshot() -> dict[str, Any]:
    try:
        metrics = load_metrics()
        feature_importance = load_feature_importance()
    except ModelUnavailableError:
        return {
            "available": False,
            "sample_count": None,
            "valid_for_research_conclusion": False,
            "metrics": None,
            "warnings": ["尚未训练模型，特征重要性暂不可用。"],
            "feature_importance": [],
        }

    return {
        "available": True,
        "model_version": metrics.get("model_version"),
        "data_source": metrics.get("data_source"),
        "sample_count": metrics.get("sample_count"),
        "valid_for_research_conclusion": bool(metrics.get("valid_for_research_conclusion", False)),
        "metrics": metrics.get("metrics"),
        "warnings": metrics.get("warnings", []),
        "feature_importance": feature_importance[:10],
    }


def get_factor_analysis(db: Session, user_id: int) -> dict[str, Any]:
    sessions = completed_user_sessions(db, user_id)
    return {
        "user_id": user_id,
        "sample_count": len(sessions),
        "time_periods": build_time_periods(sessions),
        "motion_efficiency_points": build_motion_points(sessions),
        "rule_suggestions": build_rule_suggestions(sessions),
        "model_snapshot": load_model_snapshot(),
    }
