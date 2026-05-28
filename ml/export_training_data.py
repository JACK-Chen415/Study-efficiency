from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from common import (
    DEFAULT_DATASET_PATH,
    EXPORT_COLUMNS,
    MOTION_FIELDS,
    ensure_abandon_columns,
    ensure_parent_dir,
    label_from_score,
    make_engine,
    models,
    resolve_database_url,
    sqlite_database_path,
    zero_if_missing,
)


@dataclass(frozen=True)
class ExportResult:
    sample_count: int
    abandoned_excluded: int = 0
    warning: str | None = None


def build_row(session: models.StudySession, motion: models.MotionFeature | None) -> dict:
    motion_available = 1 if motion is not None else 0
    row = {
        "session_id": session.id,
        "user_id": session.user_id,
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
        "motion_available": motion_available,
        "efficiency_score": session.efficiency_score,
        "efficiency_label": label_from_score(session.efficiency_score),
    }
    for field in MOTION_FIELDS:
        row[field] = zero_if_missing(getattr(motion, field, None)) if motion_available else 0
    return row


def write_csv(output_path: Path, rows: list[dict]) -> None:
    ensure_parent_dir(output_path)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def source_tables_ready(database_url: str) -> tuple[bool, str | None]:
    sqlite_path = sqlite_database_path(database_url)
    if sqlite_path is not None and not sqlite_path.exists():
        return False, f"SQLite database not found: {sqlite_path}"

    engine = make_engine(database_url)
    table_names = set(inspect(engine).get_table_names())
    required_tables = {"study_sessions", "motion_features"}
    missing_tables = sorted(required_tables - table_names)
    if missing_tables:
        return False, f"Missing source table(s): {', '.join(missing_tables)}"
    return True, None


def export_training_data(database_url: str, output_path: Path) -> ExportResult:
    ready, warning = source_tables_ready(database_url)
    if not ready:
        write_csv(output_path, [])
        return ExportResult(sample_count=0, warning=warning)

    engine = make_engine(database_url)
    ensure_abandon_columns(engine)
    with Session(engine) as db:
        abandoned_excluded = (
            db.query(models.StudySession)
            .filter(models.StudySession.abandoned_at.is_not(None))
            .count()
        )
        rows = (
            db.query(models.StudySession, models.MotionFeature)
            .outerjoin(models.MotionFeature, models.MotionFeature.session_id == models.StudySession.id)
            .filter(
                models.StudySession.end_time.is_not(None),
                models.StudySession.abandoned_at.is_(None),
                models.StudySession.efficiency_score.is_not(None),
            )
            .order_by(models.StudySession.id.asc())
            .all()
        )

    write_csv(output_path, [build_row(session, motion) for session, motion in rows])
    return ExportResult(sample_count=len(rows), abandoned_excluded=abandoned_excluded)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export completed study sessions and optional motion features to a training CSV."
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL. Defaults to DATABASE_URL, then backend/study_efficiency.db.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Output CSV path. Defaults to data/processed/training_dataset.csv.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database_url = resolve_database_url(args.database_url)
    result = export_training_data(database_url=database_url, output_path=args.output)
    print(f"Exported {result.sample_count} completed labeled sessions.")
    print(f"Excluded {result.abandoned_excluded} abandoned sessions.")
    print(f"Database: {database_url}")
    print(f"Output: {args.output}")
    print("Missing motion_features are exported as 0 with motion_available=0.")
    if result.warning:
        print(f"Warning: {result.warning}")


if __name__ == "__main__":
    main()
