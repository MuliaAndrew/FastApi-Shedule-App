from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_editor
from app.models import Booking, Classroom, User, UserRole
from app.schemas import (
    BookingCreate,
    BookingResponse,
    BookingUpdate,
    SuggestionRequest,
    SuggestionResponse,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _has_overlap(
    db: Session,
    classroom_id: int,
    start: datetime,
    end: datetime,
    exclude_id: int = None,
) -> bool:
    q = db.query(Booking).filter(
        Booking.classroom_id == classroom_id,
        Booking.start_time < end,
        Booking.end_time > start,
    )
    if exclude_id is not None:
        q = q.filter(Booking.id != exclude_id)
    return q.first() is not None


# ── Public read endpoints ─────────────────────────────────────────────────────

@router.get("/classroom/{classroom_id}", response_model=list[BookingResponse])
def list_classroom_bookings(classroom_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Booking)
        .filter(Booking.classroom_id == classroom_id)
        .order_by(Booking.start_time)
        .all()
    )


@router.get("/editor/{user_id}", response_model=list[BookingResponse])
def list_editor_bookings(user_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Booking)
        .filter(Booking.user_id == user_id)
        .order_by(Booking.start_time)
        .all()
    )


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


# ── Editor/admin write endpoints ──────────────────────────────────────────────

@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    if not db.query(Classroom).filter(Classroom.id == data.classroom_id).first():
        raise HTTPException(status_code=404, detail="Classroom not found")
    if _has_overlap(db, data.classroom_id, data.start_time, data.end_time):
        raise HTTPException(status_code=409, detail="Booking overlaps with an existing booking")
    booking = Booking(**data.model_dump(), user_id=current_user.id)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.patch("/{booking_id}", response_model=BookingResponse)
def update_booking(
    booking_id: int,
    data: BookingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if current_user.role == UserRole.editor and booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot modify another user's booking")

    updates = data.model_dump(exclude_unset=True)
    new_start = updates.get("start_time", booking.start_time)
    new_end = updates.get("end_time", booking.end_time)
    if new_start >= new_end:
        raise HTTPException(status_code=400, detail="start_time must be before end_time")
    if _has_overlap(db, booking.classroom_id, new_start, new_end, exclude_id=booking_id):
        raise HTTPException(
            status_code=409, detail="Updated time overlaps with an existing booking"
        )

    for field, value in updates.items():
        setattr(booking, field, value)
    booking.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(booking)
    return booking


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if current_user.role == UserRole.editor and booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot delete another user's booking")
    db.delete(booking)
    db.commit()


# ── Smart suggestion ──────────────────────────────────────────────────────────

@router.post("/suggest", response_model=SuggestionResponse)
def suggest_classrooms(
    req: SuggestionRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
):
    required_features: list[str] = [
        f
        for flag, f in [
            (req.requires_projector, "has_projector"),
            (req.requires_virtual_board, "has_virtual_board"),
            (req.requires_camera, "has_camera"),
            (req.requires_ac, "has_ac"),
        ]
        if flag
    ]

    all_classrooms: list[Classroom] = db.query(Classroom).all()

    free_classrooms = [
        c
        for c in all_classrooms
        if not _has_overlap(db, c.id, req.start_time, req.end_time)
    ]

    full_matches: list[Classroom] = []
    partial_scored: list[tuple[int, Classroom]] = []

    for classroom in free_classrooms:
        capacity_ok = classroom.capacity >= req.min_capacity
        features_met = sum(1 for f in required_features if getattr(classroom, f))
        all_features_ok = features_met == len(required_features)

        if capacity_ok and all_features_ok:
            full_matches.append(classroom)
        else:
            # Score: capacity contributes more than individual features
            score = (100 if capacity_ok else 0) + features_met
            partial_scored.append((score, classroom))

    partial_scored.sort(key=lambda x: x[0], reverse=True)
    partial_matches = [c for _, c in partial_scored]

    return SuggestionResponse(
        full_matches=full_matches[:10],
        partial_matches=partial_matches[:10] if not full_matches else [],
    )
