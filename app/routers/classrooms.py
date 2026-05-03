from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import Classroom
from app.schemas import ClassroomCreate, ClassroomResponse, ClassroomUpdate

router = APIRouter(prefix="/classrooms", tags=["classrooms"])


@router.get("", response_model=list[ClassroomResponse])
def list_classrooms(db: Session = Depends(get_db)):
    return db.query(Classroom).all()


@router.get("/{classroom_id}", response_model=ClassroomResponse)
def get_classroom(classroom_id: int, db: Session = Depends(get_db)):
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")
    return classroom


@router.post(
    "",
    response_model=ClassroomResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_classroom(data: ClassroomCreate, db: Session = Depends(get_db)):
    classroom = Classroom(**data.model_dump())
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    return classroom


@router.patch(
    "/{classroom_id}",
    response_model=ClassroomResponse,
    dependencies=[Depends(require_admin)],
)
def update_classroom(
    classroom_id: int, data: ClassroomUpdate, db: Session = Depends(get_db)
):
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(classroom, field, value)
    db.commit()
    db.refresh(classroom)
    return classroom


@router.delete(
    "/{classroom_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_classroom(classroom_id: int, db: Session = Depends(get_db)):
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")
    db.delete(classroom)
    db.commit()
