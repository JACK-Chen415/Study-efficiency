from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from . import models, schemas


REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = REPO_ROOT / "models"
MODEL_BUNDLE_PATH = MODEL_DIR / "latest.joblib"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
MODEL_DATASET_PATH = PROCESSED_DIR / "api_training_dataset.csv"
METRICS_PATH = PROCESSED_DIR / "api_model_metrics.json"
FEATURE_IMPORTANCE_PATH = PROCESSED_DIR / "api_feature_importance.csv"

MIN_TRAINING_SAMPLES = 30
EFFICIENCY_LABEL_ORDER = ["low", "medium", "high"]
TARGET_COLUMN = "efficiency_label"
EXCLUDED_FEATURE_COLUMNS = {"session_id", "user_id", "efficiency_score"}
TRAINING_FEATURE_COLUMNS = [
    "duration_minutes",
    "time_period",
    "location",
    "task_type",
    "goal_clarity",
    "light_level",
    "noise_level",
    "fatigue_level",
    "mood_stress",
    "phone_distraction",
    "move_count",
    "shake_count",
    "still_ratio",
    "avg_acceleration",
    "max_acceleration",
    "motion_available",
]
CATEGORICAL_FEATURE_COLUMNS = ["time_period", "location", "task_type"]
MOTION_FIELDS = ["move_count", "shake_count", "still_ratio", "avg_acceleration", "max_acceleration"]
EXPORT_COLUMNS = [
    "session_id",
    "user_id",
    *TRAINING_FEATURE_COLUMNS,
    "efficiency_score",
    TARGET_COLUMN,
]


class ModelServiceError(RuntimeError):
    status_code = 400


class MissingMLDependencyError(ModelServiceError):
    status_code = 409


class NotEnoughTrainingDataError(ModelServiceError):
    status_code = 422


class ModelUnavailableError(ModelServiceError):
    status_code = 409


class InvalidSessionForPredictionError(ModelServiceError):
    status_code = 422


@dataclass(frozen=True)
class LoadedDataset:
    rows: list[list[Any]]
    labels: list[str]
    feature_columns: list[str]
    categorical_features: list[str]
    numeric_features: list[str]
    skipped_rows: int
    invalid_numeric_values: int

    @property
    def sample_count(self) -> int:
        return len(self.labels)

    @property
    def label_distribution(self) -> dict[str, int]:
        return label_distribution(self.labels)


@dataclass(frozen=True)
class EvaluationSplit:
    x_train: list[list[Any]]
    x_test: list[list[Any]]
    y_train: list[str]
    y_test: list[str]
    mode: str
    warnings: list[str]
    reliable: bool


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_ml_dependencies() -> dict[str, Any]:
    try:
        import joblib
        from sklearn.compose import ColumnTransformer
        from sklearn.dummy import DummyClassifier
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.impute import SimpleImputer
        from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder
    except ImportError as exc:
        raise MissingMLDependencyError(
            "Missing ML dependency: install scikit-learn and joblib before training or predicting."
        ) from exc

    return {
        "ColumnTransformer": ColumnTransformer,
        "DummyClassifier": DummyClassifier,
        "RandomForestClassifier": RandomForestClassifier,
        "SimpleImputer": SimpleImputer,
        "accuracy_score": accuracy_score,
        "confusion_matrix": confusion_matrix,
        "joblib": joblib,
        "Pipeline": Pipeline,
        "precision_recall_fscore_support": precision_recall_fscore_support,
        "train_test_split": train_test_split,
        "OneHotEncoder": OneHotEncoder,
    }


def label_from_score(score: int | str | None) -> str | None:
    if score is None or score == "":
        return None
    score_value = int(score)
    if score_value <= 2:
        return "low"
    if score_value == 3:
        return "medium"
    return "high"


def plain_number(value: Any) -> Any:
    return float(value) if hasattr(value, "as_tuple") else value


def zero_if_missing(value: Any) -> Any:
    return 0 if value is None else plain_number(value)


def session_to_row(session: models.StudySession, motion: models.MotionFeature | None) -> dict[str, Any]:
    motion_available = 1 if motion is not None else 0
    row: dict[str, Any] = {
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
        TARGET_COLUMN: label_from_score(session.efficiency_score),
    }
    for field in MOTION_FIELDS:
        row[field] = zero_if_missing(getattr(motion, field, None)) if motion_available else 0
    return row


def completed_training_rows(db: Session) -> list[dict[str, Any]]:
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
    return [session_to_row(session, motion) for session, motion in rows]


def write_dataset(rows: list[dict[str, Any]], output_path: Path = MODEL_DATASET_PATH) -> None:
    ensure_parent_dir(output_path)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_float(value: Any) -> tuple[float, bool]:
    if value is None or value == "":
        return math.nan, False
    try:
        return float(value), False
    except (TypeError, ValueError):
        return math.nan, True


def clean_categorical(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def load_dataset_from_rows(source_rows: list[dict[str, Any]]) -> LoadedDataset:
    feature_columns = [
        column for column in EXPORT_COLUMNS if column != TARGET_COLUMN and column not in EXCLUDED_FEATURE_COLUMNS
    ]
    categorical_features = [column for column in CATEGORICAL_FEATURE_COLUMNS if column in feature_columns]
    numeric_features = [column for column in feature_columns if column not in categorical_features]

    rows: list[list[Any]] = []
    labels: list[str] = []
    skipped_rows = 0
    invalid_numeric_values = 0

    for source_row in source_rows:
        label = clean_categorical(source_row.get(TARGET_COLUMN))
        if label not in EFFICIENCY_LABEL_ORDER:
            skipped_rows += 1
            continue

        values: list[Any] = []
        for feature in feature_columns:
            if feature in categorical_features:
                values.append(clean_categorical(source_row.get(feature)))
                continue

            value, invalid = parse_float(source_row.get(feature))
            invalid_numeric_values += 1 if invalid else 0
            values.append(value)

        rows.append(values)
        labels.append(label)

    return LoadedDataset(
        rows=rows,
        labels=labels,
        feature_columns=feature_columns,
        categorical_features=categorical_features,
        numeric_features=numeric_features,
        skipped_rows=skipped_rows,
        invalid_numeric_values=invalid_numeric_values,
    )


def label_distribution(labels: list[str]) -> dict[str, int]:
    return {label: labels.count(label) for label in EFFICIENCY_LABEL_ORDER}


def make_one_hot_encoder(deps: dict[str, Any]) -> Any:
    one_hot_encoder = deps["OneHotEncoder"]
    try:
        return one_hot_encoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return one_hot_encoder(handle_unknown="ignore", sparse=False)


def build_preprocessor(dataset: LoadedDataset, deps: dict[str, Any]) -> Any:
    transformers: list[tuple[str, Any, list[int]]] = []
    pipeline = deps["Pipeline"]
    simple_imputer = deps["SimpleImputer"]
    column_transformer = deps["ColumnTransformer"]

    numeric_indices = [dataset.feature_columns.index(column) for column in dataset.numeric_features]
    categorical_indices = [dataset.feature_columns.index(column) for column in dataset.categorical_features]

    if numeric_indices:
        transformers.append(("numeric", pipeline(steps=[("imputer", simple_imputer(strategy="median"))]), numeric_indices))

    if categorical_indices:
        transformers.append(
            (
                "categorical",
                pipeline(
                    steps=[
                        ("imputer", simple_imputer(missing_values=None, strategy="most_frequent")),
                        ("onehot", make_one_hot_encoder(deps)),
                    ]
                ),
                categorical_indices,
            )
        )

    return column_transformer(transformers=transformers)


def build_random_forest_pipeline(dataset: LoadedDataset, deps: dict[str, Any], random_state: int) -> Any:
    return deps["Pipeline"](
        steps=[
            ("preprocessor", build_preprocessor(dataset, deps)),
            (
                "classifier",
                deps["RandomForestClassifier"](
                    n_estimators=200,
                    random_state=random_state,
                    class_weight="balanced",
                ),
            ),
        ]
    )


def split_dataset(
    rows: list[list[Any]],
    labels: list[str],
    deps: dict[str, Any],
    random_state: int,
    test_size: float,
) -> EvaluationSplit:
    sample_count = len(labels)
    counts = {label: labels.count(label) for label in set(labels)}
    present_label_count = len(counts)
    warnings: list[str] = []

    if sample_count < 4:
        warnings.append("样本数少于 4，使用全量数据训练并在同一数据上做流程验证。")
        return EvaluationSplit(rows, rows, labels, labels, "resubstitution_too_few_samples", warnings, False)

    can_stratify = present_label_count >= 2 and all(count >= 2 for count in counts.values())
    train_test_split = deps["train_test_split"]

    if can_stratify:
        test_count = max(present_label_count, math.ceil(sample_count * test_size))
        max_test_count = sample_count - present_label_count
        if test_count <= max_test_count:
            x_train, x_test, y_train, y_test = train_test_split(
                rows,
                labels,
                test_size=test_count,
                random_state=random_state,
                stratify=labels,
            )
            return EvaluationSplit(x_train, x_test, y_train, y_test, "stratified_train_test_split", warnings, True)

    warnings.append("标签数量或分布不足以分层划分，降级为非分层 train/test split。")
    test_count = max(1, math.ceil(sample_count * test_size))
    x_train, x_test, y_train, y_test = train_test_split(
        rows,
        labels,
        test_size=test_count,
        random_state=random_state,
        stratify=None,
    )
    if len(set(y_train)) < 2:
        warnings.append("训练集类别不足，使用全量数据训练并在同一数据上做流程验证。")
        return EvaluationSplit(rows, rows, labels, labels, "resubstitution_class_limited", warnings, False)

    return EvaluationSplit(x_train, x_test, y_train, y_test, "non_stratified_train_test_split", warnings, False)


def round_metric(value: Any) -> float:
    return round(float(value), 6)


def evaluate_predictions(y_true: list[str], y_pred: list[str], deps: dict[str, Any]) -> dict[str, Any]:
    precision_recall_fscore_support = deps["precision_recall_fscore_support"]
    precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=EFFICIENCY_LABEL_ORDER,
        average="macro",
        zero_division=0,
    )
    precision_weighted, recall_weighted, f1_weighted, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=EFFICIENCY_LABEL_ORDER,
        average="weighted",
        zero_division=0,
    )
    matrix = deps["confusion_matrix"](y_true, y_pred, labels=EFFICIENCY_LABEL_ORDER)

    return {
        "accuracy": round_metric(deps["accuracy_score"](y_true, y_pred)),
        "precision_macro": round_metric(precision_macro),
        "precision_weighted": round_metric(precision_weighted),
        "recall_macro": round_metric(recall_macro),
        "recall_weighted": round_metric(recall_weighted),
        "f1_macro": round_metric(f1_macro),
        "f1_weighted": round_metric(f1_weighted),
        "confusion_matrix": matrix.astype(int).tolist(),
    }


def transformed_feature_names(model_pipeline: Any, dataset: LoadedDataset) -> list[str]:
    feature_names: list[str] = []
    preprocessor = model_pipeline.named_steps["preprocessor"]
    if dataset.numeric_features:
        feature_names.extend(dataset.numeric_features)
    if dataset.categorical_features:
        categorical_pipeline = preprocessor.named_transformers_["categorical"]
        encoder = categorical_pipeline.named_steps["onehot"]
        if hasattr(encoder, "get_feature_names_out"):
            feature_names.extend(str(name) for name in encoder.get_feature_names_out(dataset.categorical_features))
        else:
            for feature, categories in zip(dataset.categorical_features, encoder.categories_):
                feature_names.extend(f"{feature}_{category}" for category in categories)
    return feature_names


def feature_importance_items(model_pipeline: Any, dataset: LoadedDataset) -> list[dict[str, Any]]:
    classifier = model_pipeline.named_steps["classifier"]
    if not hasattr(classifier, "feature_importances_"):
        return []
    names = transformed_feature_names(model_pipeline, dataset)
    importances = classifier.feature_importances_
    if len(names) != len(importances):
        return []
    ranked = sorted(zip(names, importances), key=lambda item: float(item[1]), reverse=True)
    return [
        {"rank": index, "feature_name": name, "importance_score": round_metric(importance)}
        for index, (name, importance) in enumerate(ranked, start=1)
    ]


def write_feature_importance(items: list[dict[str, Any]], output_path: Path = FEATURE_IMPORTANCE_PATH) -> None:
    ensure_parent_dir(output_path)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["rank", "feature_name", "importance_score"])
        writer.writeheader()
        writer.writerows(items)


def write_metrics(metrics: dict[str, Any], output_path: Path = METRICS_PATH) -> None:
    ensure_parent_dir(output_path)
    output_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def train_model(db: Session, payload: schemas.ModelTrainRequest) -> dict[str, Any]:
    if payload.model_type != "random_forest_classifier":
        raise ModelServiceError("Only random_forest_classifier is supported in the MVP.")

    rows = completed_training_rows(db)
    write_dataset(rows)
    dataset = load_dataset_from_rows(rows)
    present_labels = [label for label, count in dataset.label_distribution.items() if count > 0]

    if dataset.sample_count < MIN_TRAINING_SAMPLES:
        raise NotEnoughTrainingDataError(
            f"Need at least {MIN_TRAINING_SAMPLES} completed labeled sessions; found {dataset.sample_count}."
        )
    if len(present_labels) < 2:
        raise NotEnoughTrainingDataError("Need at least two efficiency_label classes to train a useful classifier.")

    deps = load_ml_dependencies()
    split = split_dataset(dataset.rows, dataset.labels, deps, payload.random_state, payload.test_size)
    model_pipeline = build_random_forest_pipeline(dataset, deps, payload.random_state)
    model_pipeline.fit(split.x_train, split.y_train)

    model_predictions = list(model_pipeline.predict(split.x_test))
    random_forest_metrics = evaluate_predictions(split.y_test, model_predictions, deps)

    dummy_classifier = deps["DummyClassifier"](strategy="most_frequent", random_state=payload.random_state)
    dummy_classifier.fit(split.x_train, split.y_train)
    dummy_metrics = evaluate_predictions(split.y_test, list(dummy_classifier.predict(split.x_test)), deps)

    model_version = datetime.now().strftime("rf_%Y%m%d_%H%M%S")
    trained_at = datetime.now().isoformat(timespec="seconds")
    feature_items = feature_importance_items(model_pipeline, dataset)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "pipeline": model_pipeline,
        "metadata": {
            "model_version": model_version,
            "trained_at": trained_at,
            "data_source": payload.data_source,
            "sample_count": dataset.sample_count,
            "label_distribution": dataset.label_distribution,
            "target_column": TARGET_COLUMN,
            "excluded_columns": sorted(EXCLUDED_FEATURE_COLUMNS),
            "feature_columns": dataset.feature_columns,
            "categorical_features": dataset.categorical_features,
            "numeric_features": dataset.numeric_features,
            "labels": EFFICIENCY_LABEL_ORDER,
            "random_state": payload.random_state,
            "test_size": payload.test_size,
            "valid_for_research_conclusion": payload.data_source == "real" and split.reliable,
            "metrics_output": str(METRICS_PATH),
            "feature_importance_output": str(FEATURE_IMPORTANCE_PATH),
        },
    }
    deps["joblib"].dump(bundle, MODEL_BUNDLE_PATH)

    warnings = list(split.warnings)
    if payload.data_source != "real":
        warnings.append("仅流程验证，不代表真实学习效率规律。")

    metrics = {
        "model_version": model_version,
        "trained_at": trained_at,
        "status": "trained",
        "data_source": payload.data_source,
        "sample_count": dataset.sample_count,
        "label_distribution": dataset.label_distribution,
        "valid_for_research_conclusion": payload.data_source == "real" and split.reliable,
        "warnings": warnings,
        "evaluation": {
            "mode": split.mode,
            "random_state": payload.random_state,
            "test_size": payload.test_size,
            "train_sample_count": len(split.y_train),
            "test_sample_count": len(split.y_test),
            "labels": EFFICIENCY_LABEL_ORDER,
        },
        "metrics": random_forest_metrics,
        "dummy_baseline": dummy_metrics,
        "model": {
            "type": "RandomForestClassifier",
            "n_estimators": 200,
            "class_weight": "balanced",
            "bundle_path": str(MODEL_BUNDLE_PATH),
        },
    }
    write_metrics(metrics)
    write_feature_importance(feature_items)
    return metrics


def load_metrics() -> dict[str, Any]:
    if not METRICS_PATH.exists():
        raise ModelUnavailableError("No model metrics found. Train a model first.")
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


def load_feature_importance() -> list[dict[str, Any]]:
    if not FEATURE_IMPORTANCE_PATH.exists():
        raise ModelUnavailableError("No feature importance found. Train a model first.")
    with FEATURE_IMPORTANCE_PATH.open("r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    items: list[dict[str, Any]] = []
    for row in rows:
        if not row.get("feature_name"):
            continue
        items.append(
            {
                "rank": int(row["rank"]),
                "feature_name": row["feature_name"],
                "importance_score": float(row["importance_score"]),
            }
        )
    return items


def load_model_bundle() -> dict[str, Any]:
    if not MODEL_BUNDLE_PATH.exists():
        raise ModelUnavailableError("No trained model found. Train a model first.")
    deps = load_ml_dependencies()
    return deps["joblib"].load(MODEL_BUNDLE_PATH)


def row_values_for_prediction(session: models.StudySession) -> list[Any]:
    row = session_to_row(session, session.motion_features)
    values: list[Any] = []
    for feature in TRAINING_FEATURE_COLUMNS:
        if feature in CATEGORICAL_FEATURE_COLUMNS:
            values.append(clean_categorical(row.get(feature)))
        else:
            value, _ = parse_float(row.get(feature))
            values.append(value)
    return values


def suggestion_for_session(session: models.StudySession, predicted_label: str) -> str:
    suggestions: list[str] = []
    if session.fatigue_level is not None and session.fatigue_level >= 4:
        suggestions.append("疲劳程度较高，建议先短暂休息再进入下一轮学习。")
    if session.phone_distraction is not None and session.phone_distraction >= 4:
        suggestions.append("手机干扰偏强，建议开启勿扰模式或把手机放远。")
    if session.goal_clarity is not None and session.goal_clarity <= 2:
        suggestions.append("目标清晰度偏低，建议先写下本轮学习要完成的具体任务。")
    if session.noise_level is not None and session.noise_level >= 4:
        suggestions.append("噪声较高，建议更换座位或使用降噪耳机。")
    if session.time_period == "late_night":
        suggestions.append("深夜学习可能影响状态，建议控制时长并保证睡眠。")
    if not suggestions and predicted_label == "high":
        suggestions.append("当前特征接近高效率状态，建议保持明确目标和较低手机干扰。")
    if not suggestions:
        suggestions.append("建议优先保持目标明确、降低手机干扰，并观察下一次学习表现。")
    return " ".join(suggestions)


def predict_session(db: Session, session: models.StudySession) -> models.Prediction:
    if session.end_time is None or session.abandoned_at is not None or session.efficiency_score is None:
        raise InvalidSessionForPredictionError("Only completed labeled sessions can be predicted in the MVP.")

    bundle = load_model_bundle()
    pipeline = bundle["pipeline"]
    metadata = bundle.get("metadata", {})
    probabilities = pipeline.predict_proba([row_values_for_prediction(session)])[0]
    labels = list(getattr(pipeline.named_steps["classifier"], "classes_", EFFICIENCY_LABEL_ORDER))
    best_index = max(range(len(probabilities)), key=lambda index: float(probabilities[index]))
    predicted_label = str(labels[best_index])
    confidence = round(float(probabilities[best_index]), 4)
    prediction = models.Prediction(
        session_id=session.id,
        predicted_label=predicted_label,
        confidence=confidence,
        model_version=metadata.get("model_version", "latest"),
        suggestion=suggestion_for_session(session, predicted_label),
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction
