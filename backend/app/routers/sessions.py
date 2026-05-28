from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db


router = APIRouter()


@router.post("/start", response_model=schemas.SessionStartResponse, status_code=status.HTTP_201_CREATED)
def start_session(payload: schemas.SessionStartRequest, db: Session = Depends(get_db)):
    if crud.get_user(db, payload.user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    if crud.get_open_session(db, payload.user_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="user already has an in-progress session")

    session = crud.create_session(db, user_id=payload.user_id, start_time=payload.start_time)
    return {"id": session.id, "user_id": session.user_id, "start_time": session.start_time, "status": "in_progress"}


@router.post("/end", response_model=schemas.SessionResponse)
def end_session(payload: schemas.SessionEndRequest, db: Session = Depends(get_db)):
    session = crud.get_session(db, payload.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    if session.end_time is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="session already completed")
    if session.abandoned_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="abandoned session cannot be completed")

    try:
        session = crud.end_session(db, session=session, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return crud.to_session_response(session)


@router.post("/{session_id}/abandon", response_model=schemas.SessionResponse)
def abandon_session(
    session_id: int,
    payload: schemas.SessionAbandonRequest | None = None,
    db: Session = Depends(get_db),
):
    session = crud.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    if session.end_time is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="completed session cannot be abandoned")

    session = crud.abandon_session(db, session=session, payload=payload or schemas.SessionAbandonRequest())
    return crud.to_session_response(session)


@router.get("/list", response_model=schemas.SessionListResponse)
def list_sessions(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    if user_id <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="user_id must be positive")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="limit must be between 1 and 100")
    if offset < 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="offset must be greater than or equal to 0")
    if crud.get_user(db, user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    items, total = crud.list_sessions(db, user_id=user_id, limit=limit, offset=offset)
    return {"items": [crud.to_session_response(item) for item in items], "total": total}


@router.get("/{session_id}", response_model=schemas.SessionDetailResponse)
def get_session_detail(session_id: int, db: Session = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    return crud.to_session_detail_response(session)


@router.put("/{session_id}", response_model=schemas.SessionResponse)
def update_session(session_id: int, payload: schemas.SessionUpdateRequest, db: Session = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    if session.end_time is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="only completed sessions can be edited")

    session = crud.update_session_report(db, session=session, payload=payload)
    return crud.to_session_response(session)


@router.delete("/{session_id}", response_model=schemas.SessionDeleteResponse)
def delete_session(session_id: int, db: Session = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")

    archive = crud.archive_and_delete_session(db, session)
    return crud.to_delete_response(archive)
