from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db


router = APIRouter()


@router.post("/simple-login", response_model=schemas.UserResponse)
def simple_login(
    payload: schemas.UserSimpleLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    user, created = crud.simple_login(db, payload)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return user

