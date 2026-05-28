from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, text

from common import (
    DEFAULT_DATASET_PATH,
    DEFAULT_QUALITY_REPORT_PATH,
    EFFICIENCY_LABEL_VALUES,
    LOCATION_VALUES,
    MAX_REASONABLE_DURATION_MINUTES,
    MIN_TRAINING_SAMPLES,
    MOTION_FIELDS,
    SELF_REPORT_FIELDS,
    TASK_TYPE_VALUES,
    TIME_PERIOD_VALUES,
    ensure_parent_dir,
    label_from_score,
    make_engine,
    resolve_database_url,
    sqlite_database_path,
)


def is_blank(value: str | None) -> bool:
    return value is None or value == ""


def as_int(value: str | None) -> int | None:
    if is_blank(value):
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def as_float(value: str | None) -> float | None:
    if is_blank(value):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def row_id(row: dict) -> str:
    return row.get("session_id") or "<unknown>"


def count_abandoned_sessions(database_url: str | None) -> int | None:
    if not database_url:
        return None

    sqlite_path = sqlite_database_path(database_url)
    if sqlite_path is not None and not sqlite_path.exists():
        return None

    engine = make_engine(database_url)
    inspector = inspect(engine)
    if "study_sessions" not in inspector.get_table_names():
        return None

    columns = {column["name"] for column in inspector.get_columns("study_sessions")}
    if "abandoned_at" not in columns:
        return 0

    with engine.connect() as connection:
        return int(connection.execute(text("SELECT COUNT(*) FROM study_sessions WHERE abandoned_at IS NOT NULL")).scalar() or 0)


def validate_dataset(dataset_path: Path, database_url: str | None = None) -> dict:
    with dataset_path.open("r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    label_distribution: Counter = Counter(row.get("efficiency_label") or "<missing>" for row in rows)
    missing_motion = sum(1 for row in rows if str(row.get("motion_available", "")).strip() in {"", "0", "False", "false"})

    abnormal_duration: list[str] = []
    out_of_range_self_report: list[str] = []
    enum_issues: list[str] = []
    label_mismatches: list[str] = []
    motion_value_issues: list[str] = []

    for row in rows:
        current_id = row_id(row)
        duration = as_int(row.get("duration_minutes"))
        if duration is None or duration < 1 or duration > MAX_REASONABLE_DURATION_MINUTES:
            abnormal_duration.append(current_id)

        for field in SELF_REPORT_FIELDS + ["efficiency_score"]:
            value = as_int(row.get(field))
            if value is None or value < 1 or value > 5:
                out_of_range_self_report.append(f"{current_id}:{field}")

        if row.get("time_period") not in TIME_PERIOD_VALUES:
            enum_issues.append(f"{current_id}:time_period")
        if row.get("location") not in LOCATION_VALUES:
            enum_issues.append(f"{current_id}:location")
        if row.get("task_type") not in TASK_TYPE_VALUES:
            enum_issues.append(f"{current_id}:task_type")
        if row.get("efficiency_label") not in EFFICIENCY_LABEL_VALUES:
            enum_issues.append(f"{current_id}:efficiency_label")

        expected_label = label_from_score(row.get("efficiency_score"))
        if expected_label and row.get("efficiency_label") != expected_label:
            label_mismatches.append(current_id)

        for field in MOTION_FIELDS:
            value = as_float(row.get(field))
            if value is None or value < 0:
                motion_value_issues.append(f"{current_id}:{field}")
        still_ratio = as_float(row.get("still_ratio"))
        if still_ratio is None or still_ratio < 0 or still_ratio > 1:
            motion_value_issues.append(f"{current_id}:still_ratio")

    total = len(rows)
    return {
        "dataset_path": dataset_path,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "total": total,
        "label_distribution": label_distribution,
        "missing_motion": missing_motion,
        "abnormal_duration": abnormal_duration,
        "out_of_range_self_report": out_of_range_self_report,
        "enum_issues": enum_issues,
        "label_mismatches": label_mismatches,
        "motion_value_issues": motion_value_issues,
        "meets_minimum_sample_count": total >= MIN_TRAINING_SAMPLES,
        "abandoned_source_count": count_abandoned_sessions(database_url),
    }


def format_issue_list(values: list[str]) -> str:
    if not values:
        return "0"
    preview = ", ".join(values[:20])
    suffix = "" if len(values) <= 20 else f" ... (+{len(values) - 20} more)"
    return f"{len(values)} ({preview}{suffix})"


def render_report(result: dict) -> str:
    labels = result["label_distribution"]
    minimum_status = "PASS" if result["meets_minimum_sample_count"] else "FAIL"
    lines = [
        "# Training Dataset Quality Report",
        "",
        f"- Checked at: {result['checked_at']}",
        f"- Dataset: `{result['dataset_path']}`",
        f"- Total samples: {result['total']}",
        f"- Label distribution: low={labels['low']}, medium={labels['medium']}, high={labels['high']}",
        f"- Missing motion feature rows: {result['missing_motion']}",
        f"- Abandoned source sessions excluded from dataset: {result['abandoned_source_count'] if result['abandoned_source_count'] is not None else 'not checked'}",
        f"- Abnormal duration records (<1 or >{MAX_REASONABLE_DURATION_MINUTES} minutes): {format_issue_list(result['abnormal_duration'])}",
        f"- Self-report out-of-range records: {format_issue_list(result['out_of_range_self_report'])}",
        f"- Enum value issues: {format_issue_list(result['enum_issues'])}",
        f"- Label conversion mismatches: {format_issue_list(result['label_mismatches'])}",
        f"- Motion value issues: {format_issue_list(result['motion_value_issues'])}",
        f"- Minimum training sample count ({MIN_TRAINING_SAMPLES}): {minimum_status}",
        "",
        "Note: This report checks readiness for later training only. It is not a model evaluation result.",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check exported training CSV quality before model training.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Training CSV path. Defaults to data/processed/training_dataset.csv.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_QUALITY_REPORT_PATH,
        help="Markdown report path. Defaults to data/processed/data_quality_report.md.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional source database URL used to count abandoned sessions excluded from the dataset.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(f"Dataset not found: {args.input}")

    result = validate_dataset(args.input, database_url=resolve_database_url(args.database_url))
    report = render_report(result)
    ensure_parent_dir(args.report)
    args.report.write_text(report, encoding="utf-8")

    print(report)
    print(f"Report written to: {args.report}")


if __name__ == "__main__":
    main()
