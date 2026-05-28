from __future__ import annotations

import argparse
import random
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from common import (
    DEFAULT_DEMO_DB_PATH,
    demo_database_url,
    ensure_parent_dir,
    init_tables,
    make_engine,
    models,
    resolve_database_url,
)
from app.crud import get_efficiency_label, get_time_period


LOCATION_BY_LABEL = {
    "low": ["dormitory", "other", "classroom"],
    "medium": ["classroom", "study_room", "library"],
    "high": ["library", "study_room", "classroom"],
}
TASK_BY_LABEL = {
    "low": ["coursework", "other", "exam_review"],
    "medium": ["coursework", "paper_reading", "exam_review"],
    "high": ["coding", "exam_review", "paper_reading", "postgraduate_prep"],
}
SCORE_BY_LABEL = {
    "low": [1, 2],
    "medium": [3],
    "high": [4, 5],
}


def bounded(value: int, low: int = 1, high: int = 5) -> int:
    return max(low, min(high, value))


def self_report_for_label(label: str, rng: random.Random) -> dict[str, int]:
    if label == "low":
        return {
            "goal_clarity": bounded(rng.choice([1, 2, 3])),
            "light_level": bounded(rng.choice([1, 2, 3])),
            "noise_level": bounded(rng.choice([3, 4, 5])),
            "fatigue_level": bounded(rng.choice([4, 5])),
            "mood_stress": bounded(rng.choice([4, 5])),
            "phone_distraction": bounded(rng.choice([4, 5])),
        }
    if label == "medium":
        return {
            "goal_clarity": bounded(rng.choice([3, 4])),
            "light_level": bounded(rng.choice([3, 4])),
            "noise_level": bounded(rng.choice([2, 3, 4])),
            "fatigue_level": bounded(rng.choice([2, 3, 4])),
            "mood_stress": bounded(rng.choice([2, 3, 4])),
            "phone_distraction": bounded(rng.choice([2, 3])),
        }
    return {
        "goal_clarity": bounded(rng.choice([4, 5])),
        "light_level": bounded(rng.choice([4, 5])),
        "noise_level": bounded(rng.choice([1, 2])),
        "fatigue_level": bounded(rng.choice([1, 2, 3])),
        "mood_stress": bounded(rng.choice([1, 2])),
        "phone_distraction": bounded(rng.choice([1, 2])),
    }


def motion_for_label(label: str, rng: random.Random) -> dict:
    if label == "low":
        move_count = rng.randint(18, 55)
        shake_count = rng.randint(3, 10)
        still_ratio = rng.uniform(0.35, 0.68)
    elif label == "medium":
        move_count = rng.randint(8, 24)
        shake_count = rng.randint(1, 4)
        still_ratio = rng.uniform(0.62, 0.84)
    else:
        move_count = rng.randint(0, 12)
        shake_count = rng.randint(0, 2)
        still_ratio = rng.uniform(0.78, 0.96)

    avg_acceleration = rng.uniform(0.05, 0.32) + move_count / 500
    max_acceleration = avg_acceleration + rng.uniform(0.5, 2.6)
    return {
        "move_count": move_count,
        "shake_count": shake_count,
        "still_ratio": round(still_ratio, 4),
        "avg_acceleration": round(avg_acceleration, 4),
        "max_acceleration": round(max_acceleration, 4),
    }


def label_sequence(count: int) -> list[str]:
    labels = ["low", "medium", "high"]
    return [labels[index % len(labels)] for index in range(count)]


def seed_demo_data(database_url: str, count: int, random_seed: int) -> Counter:
    rng = random.Random(random_seed)
    engine = make_engine(database_url)
    init_tables(engine)

    created_at = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_start = datetime(2026, 5, 1, 8, 30)
    counts: Counter = Counter()

    with Session(engine) as db:
        user = models.User(
            nickname=f"demo_mock_student_{created_at}",
            grade="demo",
            major="mock_data_for_development",
        )
        db.add(user)
        db.flush()

        for index, intended_label in enumerate(label_sequence(count)):
            score = rng.choice(SCORE_BY_LABEL[intended_label])
            efficiency_label = get_efficiency_label(score)
            start_time = base_start + timedelta(days=index // 3, hours=(index % 4) * 4)
            duration_minutes = rng.randint(25, 95) if intended_label != "low" else rng.randint(10, 55)
            if intended_label == "high":
                duration_minutes = rng.randint(45, 130)
            end_time = start_time + timedelta(minutes=duration_minutes)

            session = models.StudySession(
                user_id=user.id,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
                time_period=get_time_period(start_time),
                location=rng.choice(LOCATION_BY_LABEL[intended_label]),
                task_type=rng.choice(TASK_BY_LABEL[intended_label]),
                efficiency_score=score,
                efficiency_label=efficiency_label,
                **self_report_for_label(intended_label, rng),
            )
            db.add(session)
            db.flush()

            if index % 5 != 0:
                db.add(models.MotionFeature(session_id=session.id, **motion_for_label(intended_label, rng)))

            counts[efficiency_label] += 1

        db.commit()

    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create deterministic demo/mock study sessions for development testing."
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Target database URL. Defaults to a separate SQLite demo DB under data/demo/.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=36,
        help="Number of demo/mock completed sessions to create. Use at least 3 to cover all labels.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed for reproducible demo/mock values.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.count < 3:
        raise SystemExit("--count must be at least 3 so low/medium/high are all covered.")

    if args.database_url:
        database_url = resolve_database_url(args.database_url)
    else:
        ensure_parent_dir(DEFAULT_DEMO_DB_PATH)
        database_url = demo_database_url()

    counts = seed_demo_data(database_url=database_url, count=args.count, random_seed=args.random_seed)
    print("Created demo/mock study sessions for development testing only.")
    print(f"Database: {database_url}")
    print(f"Total: {sum(counts.values())}")
    print(f"Label distribution: low={counts['low']}, medium={counts['medium']}, high={counts['high']}")
    print("Do not report these demo/mock rows as real experiment conclusions.")
    print("Export example:")
    print(f"  python ml/export_training_data.py --database-url {database_url}")


if __name__ == "__main__":
    main()
