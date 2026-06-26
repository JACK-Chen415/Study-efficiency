from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from .common import (
        CATEGORICAL_FEATURE_COLUMNS,
        DEFAULT_DATASET_PATH,
        DEFAULT_FEATURE_IMPORTANCE_OUTPUT_PATH,
        DEFAULT_METRICS_OUTPUT_PATH,
        DEFAULT_MODEL_BUNDLE_PATH,
        DEFAULT_MODEL_DIR,
        EFFICIENCY_LABEL_ORDER,
        MIN_TRAINING_SAMPLES,
        NUMERIC_FEATURE_COLUMNS,
        TRAINING_FEATURE_COLUMNS,
        ensure_parent_dir,
    )
except ImportError:
    from common import (
        CATEGORICAL_FEATURE_COLUMNS,
        DEFAULT_DATASET_PATH,
        DEFAULT_FEATURE_IMPORTANCE_OUTPUT_PATH,
        DEFAULT_METRICS_OUTPUT_PATH,
        DEFAULT_MODEL_BUNDLE_PATH,
        DEFAULT_MODEL_DIR,
        EFFICIENCY_LABEL_ORDER,
        MIN_TRAINING_SAMPLES,
        NUMERIC_FEATURE_COLUMNS,
        TRAINING_FEATURE_COLUMNS,
        ensure_parent_dir,
    )


TARGET_COLUMN = "efficiency_label"
EXCLUDED_FEATURE_COLUMNS = {"session_id", "user_id", "efficiency_score"}
NON_REAL_DATA_WARNING = "仅流程验证，不代表真实学习效率规律。"
DEFAULT_RANDOM_STATE = 42


class MissingMLDependencyError(RuntimeError):
    pass


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
        counts = Counter(self.labels)
        return {label: counts.get(label, 0) for label in EFFICIENCY_LABEL_ORDER}


@dataclass(frozen=True)
class EvaluationSplit:
    x_train: list[list[Any]]
    x_test: list[list[Any]]
    y_train: list[str]
    y_test: list[str]
    mode: str
    warnings: list[str]
    reliable: bool


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
            "Missing ML dependency. This script requires scikit-learn and joblib; "
            "install the project ML dependencies before running training."
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


def parse_float(value: str | None) -> tuple[float, bool]:
    if value is None or value.strip() == "":
        return math.nan, False
    try:
        return float(value), False
    except ValueError:
        return math.nan, True


def clean_categorical(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def read_dataset(dataset_path: Path) -> LoadedDataset:
    if not dataset_path.exists():
        raise SystemExit(f"Dataset not found: {dataset_path}")

    with dataset_path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames or []
        required_columns = [TARGET_COLUMN, *TRAINING_FEATURE_COLUMNS]
        missing_columns = [column for column in required_columns if column not in fieldnames]
        if missing_columns:
            raise SystemExit(f"Dataset is missing required column(s): {', '.join(missing_columns)}")

        feature_columns = [
            column
            for column in fieldnames
            if column != TARGET_COLUMN and column not in EXCLUDED_FEATURE_COLUMNS
        ]
        categorical_features = [
            column for column in CATEGORICAL_FEATURE_COLUMNS if column in feature_columns
        ]
        numeric_features = [column for column in feature_columns if column not in categorical_features]

        rows: list[list[Any]] = []
        labels: list[str] = []
        skipped_rows = 0
        invalid_numeric_values = 0

        for row in reader:
            label = (row.get(TARGET_COLUMN) or "").strip()
            if label not in EFFICIENCY_LABEL_ORDER:
                skipped_rows += 1
                continue

            values: list[Any] = []
            for feature in feature_columns:
                if feature in categorical_features:
                    values.append(clean_categorical(row.get(feature)))
                    continue

                value, invalid = parse_float(row.get(feature))
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

    numeric_indices = [
        dataset.feature_columns.index(column) for column in dataset.numeric_features
    ]
    categorical_indices = [
        dataset.feature_columns.index(column) for column in dataset.categorical_features
    ]

    if numeric_indices:
        numeric_transformer = pipeline(
            steps=[("imputer", simple_imputer(strategy="median"))]
        )
        transformers.append(("numeric", numeric_transformer, numeric_indices))

    if categorical_indices:
        categorical_transformer = pipeline(
            steps=[
                ("imputer", simple_imputer(missing_values=None, strategy="most_frequent")),
                ("onehot", make_one_hot_encoder(deps)),
            ]
        )
        transformers.append(("categorical", categorical_transformer, categorical_indices))

    return column_transformer(transformers=transformers)


def build_random_forest_pipeline(
    dataset: LoadedDataset,
    deps: dict[str, Any],
    random_state: int,
) -> Any:
    pipeline = deps["Pipeline"]
    random_forest = deps["RandomForestClassifier"]
    return pipeline(
        steps=[
            ("preprocessor", build_preprocessor(dataset, deps)),
            (
                "classifier",
                random_forest(
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
    label_counts = Counter(labels)
    present_label_count = len(label_counts)
    warnings: list[str] = []

    if sample_count < 4:
        warnings.append("样本数少于 4，使用全量数据训练并在同一数据上做流程验证。")
        return EvaluationSplit(rows, rows, labels, labels, "resubstitution_too_few_samples", warnings, False)

    can_stratify = present_label_count >= 2 and all(count >= 2 for count in label_counts.values())
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
            return EvaluationSplit(
                x_train,
                x_test,
                y_train,
                y_test,
                "stratified_train_test_split",
                warnings,
                True,
            )

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
    accuracy_score = deps["accuracy_score"]
    confusion_matrix = deps["confusion_matrix"]

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
    matrix = confusion_matrix(y_true, y_pred, labels=EFFICIENCY_LABEL_ORDER)

    return {
        "accuracy": round_metric(accuracy_score(y_true, y_pred)),
        "precision_macro": round_metric(precision_macro),
        "precision_weighted": round_metric(precision_weighted),
        "recall_macro": round_metric(recall_macro),
        "recall_weighted": round_metric(recall_weighted),
        "f1_macro": round_metric(f1_macro),
        "f1_weighted": round_metric(f1_weighted),
        "confusion_matrix": matrix.astype(int).tolist(),
    }


def build_dummy_classifier(deps: dict[str, Any], random_state: int) -> Any:
    dummy_classifier = deps["DummyClassifier"]
    return dummy_classifier(strategy="most_frequent", random_state=random_state)


def transformed_feature_names(model_pipeline: Any, dataset: LoadedDataset) -> list[str]:
    feature_names: list[str] = []
    preprocessor = model_pipeline.named_steps["preprocessor"]

    if dataset.numeric_features:
        feature_names.extend(dataset.numeric_features)

    if dataset.categorical_features:
        categorical_pipeline = preprocessor.named_transformers_["categorical"]
        encoder = categorical_pipeline.named_steps["onehot"]
        if hasattr(encoder, "get_feature_names_out"):
            encoded = encoder.get_feature_names_out(dataset.categorical_features)
            feature_names.extend(str(name) for name in encoded)
        else:
            for feature, categories in zip(dataset.categorical_features, encoder.categories_):
                feature_names.extend(f"{feature}_{category}" for category in categories)

    return feature_names


def write_feature_importance(
    output_path: Path,
    model_pipeline: Any | None,
    dataset: LoadedDataset,
    note: str | None = None,
) -> list[str]:
    ensure_parent_dir(output_path)
    fieldnames = ["rank", "feature", "importance", "note"]
    feature_names: list[str] = []

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        if model_pipeline is None:
            writer.writerow({"rank": "", "feature": "", "importance": "", "note": note or "model not trained"})
            return feature_names

        classifier = model_pipeline.named_steps["classifier"]
        if not hasattr(classifier, "feature_importances_"):
            writer.writerow(
                {
                    "rank": "",
                    "feature": "",
                    "importance": "",
                    "note": "classifier does not expose feature_importances_",
                }
            )
            return feature_names

        feature_names = transformed_feature_names(model_pipeline, dataset)
        importances = classifier.feature_importances_
        if len(feature_names) != len(importances):
            writer.writerow(
                {
                    "rank": "",
                    "feature": "",
                    "importance": "",
                    "note": "feature name count does not match model importance count",
                }
            )
            return feature_names

        ranked = sorted(
            enumerate(zip(feature_names, importances), start=1),
            key=lambda item: float(item[1][1]),
            reverse=True,
        )
        for rank, (feature, importance) in enumerate((item[1] for item in ranked), start=1):
            writer.writerow(
                {
                    "rank": rank,
                    "feature": feature,
                    "importance": round_metric(importance),
                    "note": "",
                }
            )

    return feature_names


def write_metrics(output_path: Path, metrics: dict[str, Any]) -> None:
    ensure_parent_dir(output_path)
    output_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_base_metrics(
    args: argparse.Namespace,
    dataset: LoadedDataset,
    model_version: str,
    status: str,
    warnings: list[str],
) -> dict[str, Any]:
    valid_for_research_conclusion = (
        args.data_source == "real"
        and dataset.sample_count >= MIN_TRAINING_SAMPLES
        and len([count for count in dataset.label_distribution.values() if count > 0]) >= 2
        and status == "success"
    )

    return {
        "model_version": model_version,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "dataset": str(args.dataset),
        "data_source": args.data_source,
        "sample_count": dataset.sample_count,
        "label_distribution": dataset.label_distribution,
        "valid_for_research_conclusion": valid_for_research_conclusion,
        "warning": NON_REAL_DATA_WARNING if args.data_source != "real" else None,
        "warnings": warnings,
        "target_column": TARGET_COLUMN,
        "excluded_columns": sorted(EXCLUDED_FEATURE_COLUMNS),
        "feature_columns": dataset.feature_columns,
        "categorical_features": dataset.categorical_features,
        "numeric_features": dataset.numeric_features,
        "skipped_rows": dataset.skipped_rows,
        "invalid_numeric_values": dataset.invalid_numeric_values,
    }


def append_validity_warnings(args: argparse.Namespace, dataset: LoadedDataset, warnings: list[str]) -> None:
    if args.data_source != "real":
        warnings.append(NON_REAL_DATA_WARNING)
    elif dataset.sample_count < MIN_TRAINING_SAMPLES:
        warnings.append(
            f"真实样本数 {dataset.sample_count} 少于 {MIN_TRAINING_SAMPLES}，不适合形成正式研究结论。"
        )

    if dataset.skipped_rows:
        warnings.append(f"跳过 {dataset.skipped_rows} 行标签缺失或非法记录。")
    if dataset.invalid_numeric_values:
        warnings.append(f"发现 {dataset.invalid_numeric_values} 个非法数值，已按缺失值进入预处理。")


def train_and_evaluate(args: argparse.Namespace, deps: dict[str, Any]) -> dict[str, Any]:
    dataset = read_dataset(args.dataset)
    model_version = datetime.now().strftime("rf_%Y%m%d_%H%M%S")
    warnings: list[str] = []
    append_validity_warnings(args, dataset, warnings)

    present_labels = [label for label, count in dataset.label_distribution.items() if count > 0]
    if dataset.sample_count == 0:
        metrics = build_base_metrics(args, dataset, model_version, "failed", warnings)
        metrics["failure_reason"] = "No valid labeled rows found in dataset."
        metrics["evaluation"] = None
        metrics["random_forest"] = None
        metrics["dummy_baseline"] = None
        write_metrics(args.metrics_output, metrics)
        write_feature_importance(args.feature_importance_output, None, dataset, metrics["failure_reason"])
        raise SystemExit(metrics["failure_reason"])

    if len(present_labels) < 2:
        reason = "Need at least two efficiency_label classes to train a useful classifier."
        warnings.append("有效标签类别少于 2，未训练模型。")
        metrics = build_base_metrics(args, dataset, model_version, "failed", warnings)
        metrics["failure_reason"] = reason
        metrics["evaluation"] = None
        metrics["random_forest"] = None
        metrics["dummy_baseline"] = None
        write_metrics(args.metrics_output, metrics)
        write_feature_importance(args.feature_importance_output, None, dataset, reason)
        raise SystemExit(reason)

    split = split_dataset(dataset.rows, dataset.labels, deps, args.random_state, args.test_size)
    warnings.extend(split.warnings)

    model_pipeline = build_random_forest_pipeline(dataset, deps, args.random_state)
    model_pipeline.fit(split.x_train, split.y_train)
    model_predictions = list(model_pipeline.predict(split.x_test))
    random_forest_metrics = evaluate_predictions(split.y_test, model_predictions, deps)

    dummy_classifier = build_dummy_classifier(deps, args.random_state)
    dummy_classifier.fit(split.x_train, split.y_train)
    dummy_predictions = list(dummy_classifier.predict(split.x_test))
    dummy_metrics = evaluate_predictions(split.y_test, dummy_predictions, deps)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    model_bundle_path = output_dir / DEFAULT_MODEL_BUNDLE_PATH.name
    feature_names_out = write_feature_importance(args.feature_importance_output, model_pipeline, dataset)

    metrics = build_base_metrics(args, dataset, model_version, "success", warnings)
    metrics["valid_for_research_conclusion"] = (
        metrics["valid_for_research_conclusion"] and split.reliable
    )
    metrics["evaluation"] = {
        "mode": split.mode,
        "random_state": args.random_state,
        "train_sample_count": len(split.y_train),
        "test_sample_count": len(split.y_test),
        "labels": EFFICIENCY_LABEL_ORDER,
    }
    metrics["random_forest"] = random_forest_metrics
    metrics["dummy_baseline"] = dummy_metrics
    metrics["model"] = {
        "type": "RandomForestClassifier",
        "n_estimators": 200,
        "class_weight": "balanced",
        "bundle_path": str(model_bundle_path),
    }
    metrics["feature_importance_output"] = str(args.feature_importance_output)

    bundle = {
        "pipeline": model_pipeline,
        "metadata": {
            "model_version": model_version,
            "trained_at": metrics["trained_at"],
            "data_source": args.data_source,
            "sample_count": dataset.sample_count,
            "label_distribution": dataset.label_distribution,
            "target_column": TARGET_COLUMN,
            "excluded_columns": sorted(EXCLUDED_FEATURE_COLUMNS),
            "feature_columns": dataset.feature_columns,
            "categorical_features": dataset.categorical_features,
            "numeric_features": dataset.numeric_features,
            "labels": EFFICIENCY_LABEL_ORDER,
            "feature_names_out": feature_names_out,
            "random_state": args.random_state,
            "valid_for_research_conclusion": metrics["valid_for_research_conclusion"],
            "metrics_output": str(args.metrics_output),
            "feature_importance_output": str(args.feature_importance_output),
        },
    }
    deps["joblib"].dump(bundle, model_bundle_path)
    write_metrics(args.metrics_output, metrics)
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train an offline RandomForest efficiency classifier from the exported training CSV."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Input training CSV. Defaults to data/processed/training_dataset.csv.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_MODEL_DIR,
        help="Directory for model artifacts. Defaults to models.",
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=DEFAULT_METRICS_OUTPUT_PATH,
        help="Metrics JSON path. Defaults to data/processed/model_metrics.json.",
    )
    parser.add_argument(
        "--feature-importance-output",
        type=Path,
        default=DEFAULT_FEATURE_IMPORTANCE_OUTPUT_PATH,
        help="Feature importance CSV path. Defaults to data/processed/feature_importance.csv.",
    )
    parser.add_argument(
        "--data-source",
        choices=["real", "demo", "mock", "test"],
        default="demo",
        help="Data provenance. Non-real values are marked as flow validation only.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=DEFAULT_RANDOM_STATE,
        help=f"Random seed. Defaults to {DEFAULT_RANDOM_STATE}.",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.25,
        help="Test split ratio used for train/test evaluation. Defaults to 0.25.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 0 < args.test_size < 1:
        raise SystemExit("--test-size must be between 0 and 1.")
    try:
        deps = load_ml_dependencies()
    except MissingMLDependencyError as exc:
        dataset = read_dataset(args.dataset)
        warnings: list[str] = []
        append_validity_warnings(args, dataset, warnings)
        warnings.append(str(exc))
        model_version = datetime.now().strftime("rf_%Y%m%d_%H%M%S")
        metrics = build_base_metrics(args, dataset, model_version, "failed", warnings)
        metrics["failure_reason"] = str(exc)
        metrics["evaluation"] = None
        metrics["random_forest"] = None
        metrics["dummy_baseline"] = None
        write_metrics(args.metrics_output, metrics)
        write_feature_importance(args.feature_importance_output, None, dataset, str(exc))
        print(str(exc))
        print(f"Metrics: {args.metrics_output}")
        print(f"Feature importance: {args.feature_importance_output}")
        raise SystemExit(1) from exc

    metrics = train_and_evaluate(args, deps)
    rf = metrics["random_forest"]
    baseline = metrics["dummy_baseline"]
    print(f"Status: {metrics['status']}")
    print(f"Data source: {metrics['data_source']}")
    print(f"Sample count: {metrics['sample_count']}")
    print(f"Label distribution: {metrics['label_distribution']}")
    print(f"RandomForest accuracy: {rf['accuracy']}, f1_macro: {rf['f1_macro']}")
    print(f"Dummy baseline accuracy: {baseline['accuracy']}, f1_macro: {baseline['f1_macro']}")
    print(f"Valid for research conclusion: {metrics['valid_for_research_conclusion']}")
    if metrics.get("warning"):
        print(f"Warning: {metrics['warning']}")
    print(f"Metrics: {args.metrics_output}")
    print(f"Feature importance: {args.feature_importance_output}")
    print(f"Model bundle: {args.output_dir / DEFAULT_MODEL_BUNDLE_PATH.name}")


if __name__ == "__main__":
    main()
