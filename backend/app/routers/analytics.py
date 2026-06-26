from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import analytics_service, crud, schemas
from ..database import get_db


router = APIRouter()


def ensure_user(db: Session, user_id: int) -> None:
    if user_id <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="user_id must be positive")
    if crud.get_user(db, user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")


@router.get("/overview", response_model=schemas.AnalyticsOverviewResponse)
def overview(user_id: int, db: Session = Depends(get_db)):
    ensure_user(db, user_id)
    return analytics_service.get_overview(db, user_id)


@router.get("/trend", response_model=schemas.AnalyticsTrendResponse)
def trend(user_id: int, db: Session = Depends(get_db)):
    ensure_user(db, user_id)
    return analytics_service.get_trend(db, user_id)


@router.get("/factor-analysis", response_model=schemas.AnalyticsFactorAnalysisResponse)
def factor_analysis(user_id: int, db: Session = Depends(get_db)):
    ensure_user(db, user_id)
    return analytics_service.get_factor_analysis(db, user_id)
