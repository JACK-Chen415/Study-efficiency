from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

try:
    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.engine import Engine
    from sqlalchemy.engine import make_url
    from sqlalchemy.pool import StaticPool
except ModuleNotFoundError:  # pragma: no cover - allows offline ML scripts to import constants.
    create_engine = None
    inspect = None
    text = None
    Engine = Any
    make_url = None
    StaticPool = None


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:  # noqa: E402
    from app import models  # type: ignore
    from app.database import Base  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - allows pure-CSV tooling without backend deps.
    models = None
    Base = None


DEFAULT_BACKEND_DB_PATH = BACKEND_ROOT / "study_efficiency.db"
DEFAULT_DEMO_DB_PATH = REPO_ROOT / "data" / "demo" / "study_efficiency_demo.db"
DEFAULT_DATASET_PATH = REPO_ROOT / "data" / "processed" / "training_dataset.csv"
DEFAULT_QUALITY_REPORT_PATH = REPO_ROOT / "data" / "processed" / "data_quality_report.md"
DEFAULT_MODEL_DIR = REPO_ROOT / "models"
DEFAULT_METRICS_OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "model_metrics.json"
DEFAULT_FEATURE_IMPORTANCE_OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "feature_importance.csv"
DEFAULT_MODEL_BUNDLE_PATH = DEFAULT_MODEL_DIR / "latest.joblib"

MIN_TRAINING_SAMPLES = 30
MAX_REASONABLE_DURATION_MINUTES = 12 * 60

EFFICIENCY_LABEL_ORDER = ["low", "medium", "high"]
TIME_PERIOD_VALUES = {"morning", "afternoon", "evening", "late_night"}
LOCATION_VALUES = {"dormitory", "library", "classroom", "study_room", "other"}
TASK_TYPE_VALUES = {
    "coursework",
    "exam_review",
    "coding",
    "paper_reading",
    "postgraduate_prep",
    "other",
}
EFFICIENCY_LABEL_VALUES = {"low", "medium", "high"}

SELF_REPORT_FIELDS = [
    "goal_clarity",
    "light_level",
    "noise_level",
    "fatigue_level",
    "mood_stress",
    "phone_distraction",
]

MOTION_FIELDS = [
    "move_count",
    "shake_count",
    "still_ratio",
    "avg_acceleration",
    "max_acceleration",
]

TRAINING_FEATURE_COLUMNS = [
    "duration_minutes",
    "time_period",
    "location",
    "task_type",
    *SELF_REPORT_FIELDS,
    *MOTION_FIELDS,
    "motion_available",
]

CATEGORICAL_FEATURE_COLUMNS = ["time_period", "location", "task_type"]
NUMERIC_FEATURE_COLUMNS = [
    column for column in TRAINING_FEATURE_COLUMNS if column not in CATEGORICAL_FEATURE_COLUMNS
]

EXPORT_COLUMNS = [
    "session_id",
    "user_id",
    *TRAINING_FEATURE_COLUMNS,
    "efficiency_score",
    "efficiency_label",
]


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.resolve()}"


def default_database_url() -> str:
    return sqlite_url(DEFAULT_BACKEND_DB_PATH)


def demo_database_url() -> str:
    return sqlite_url(DEFAULT_DEMO_DB_PATH)


def resolve_database_url(database_url: str | None = None) -> str:
    return database_url or os.getenv("DATABASE_URL") or default_database_url()


def engine_kwargs(database_url: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if database_url in {"sqlite://", "sqlite:///:memory:"} and StaticPool is not None:
            kwargs["poolclass"] = StaticPool
    return kwargs


def make_engine(database_url: str) -> Engine:
    if create_engine is None:
        raise ModuleNotFoundError(
            "SQLAlchemy is unavailable in this Python environment; database export tools need backend dependencies."
        )
    return create_engine(database_url, **engine_kwargs(database_url))


def sqlite_database_path(database_url: str) -> Path | None:
    if make_url is None:
        if not database_url.startswith("sqlite:"):
            return None
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            return None
        if database_url.startswith("sqlite:///"):
            raw_path = database_url.replace("sqlite:///", "", 1)
            if raw_path == ":memory:":
                return None
            return Path(raw_path)
        return None

    url = make_url(database_url)
    if not url.drivername.startswith("sqlite") or not url.database or url.database == ":memory:":
        return None
    return Path(url.database)


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def init_tables(engine: Engine) -> None:
    if Base is None:
        raise ModuleNotFoundError(
            "SQLAlchemy backend models are unavailable in this Python environment."
        )
    Base.metadata.create_all(bind=engine)
    ensure_abandon_columns(engine)


def ensure_abandon_columns(engine: Engine) -> None:
    if inspect is None or text is None:
        raise ModuleNotFoundError(
            "SQLAlchemy backend models are unavailable in this Python environment."
        )
    inspector = inspect(engine)
    if "study_sessions" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("study_sessions")}
    statements = {
        "abandoned_at": "ALTER TABLE study_sessions ADD COLUMN abandoned_at DATETIME NULL",
        "abandon_reason": "ALTER TABLE study_sessions ADD COLUMN abandon_reason VARCHAR(100) NULL",
    }
    with engine.begin() as connection:
        for column_name, statement in statements.items():
            if column_name not in existing_columns:
                connection.execute(text(statement))


def to_plain_number(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def zero_if_missing(value: Any) -> Any:
    if value is None:
        return 0
    return to_plain_number(value)


def label_from_score(score: int | str | None) -> str | None:
    if score is None or score == "":
        return None
    score_value = int(score)
    if score_value <= 2:
        return "low"
    if score_value == 3:
        return "medium"
    return "high"
