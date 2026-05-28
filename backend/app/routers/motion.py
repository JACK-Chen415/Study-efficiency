from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db


router = APIRouter()


@router.post("/upload", response_model=schemas.MotionFeatureResponse)
def upload_motion_feature(
    payload: schemas.MotionFeatureUploadRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    if crud.get_session(db, payload.session_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")

    motion_feature, created = crud.upsert_motion_feature(db, payload)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return motion_feature


@router.get("/{session_id}", response_model=schemas.MotionFeatureResponse)
def get_motion_feature(session_id: int, db: Session = Depends(get_db)):
    motion_feature = crud.get_motion_feature(db, session_id)
    if motion_feature is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="motion features not found")
    return motion_feature

