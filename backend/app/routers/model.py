from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..model_service import (
    InvalidSessionForPredictionError,
    MissingMLDependencyError,
    ModelServiceError,
    ModelUnavailableError,
    NotEnoughTrainingDataError,
    load_feature_importance,
    load_metrics,
    predict_session,
    train_model,
)


router = APIRouter()


def _raise_service_error(exc: ModelServiceError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/train", response_model=schemas.ModelTrainResponse, status_code=status.HTTP_201_CREATED)
def train(payload: schemas.ModelTrainRequest, db: Session = Depends(get_db)):
    try:
        return train_model(db, payload)
    except NotEnoughTrainingDataError as exc:
        _raise_service_error(exc)
    except MissingMLDependencyError as exc:
        _raise_service_error(exc)
    except ModelServiceError as exc:
        _raise_service_error(exc)


@router.post("/predict", response_model=schemas.PredictionResponse, status_code=status.HTTP_201_CREATED)
def predict(payload: schemas.ModelPredictRequest, db: Session = Depends(get_db)):
    session = crud.get_session(db, payload.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    try:
        prediction = predict_session(db, session)
    except ModelUnavailableError as exc:
        _raise_service_error(exc)
    except InvalidSessionForPredictionError as exc:
        _raise_service_error(exc)
    except ModelServiceError as exc:
        _raise_service_error(exc)
    return prediction


@router.get("/metrics", response_model=schemas.ModelMetricsResponse)
def metrics():
    try:
        data = load_metrics()
    except ModelUnavailableError as exc:
        _raise_service_error(exc)
    return data


@router.get("/feature-importance", response_model=schemas.FeatureImportanceResponse)
def feature_importance():
    try:
        items = load_feature_importance()
        metrics = load_metrics()
    except ModelUnavailableError as exc:
        _raise_service_error(exc)
    return {"model_version": metrics["model_version"], "items": items}
