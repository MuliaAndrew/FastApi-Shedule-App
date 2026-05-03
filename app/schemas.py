from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

from app.models import BookingType, UserRole


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


# ── Users ─────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Classrooms ────────────────────────────────────────────────────────────────

class ClassroomCreate(BaseModel):
    number: str
    building: str
    capacity: int
    has_projector: bool = False
    has_virtual_board: bool = False
    has_camera: bool = False
    has_ac: bool = False


class ClassroomUpdate(BaseModel):
    number: Optional[str] = None
    building: Optional[str] = None
    capacity: Optional[int] = None
    has_projector: Optional[bool] = None
    has_virtual_board: Optional[bool] = None
    has_camera: Optional[bool] = None
    has_ac: Optional[bool] = None


class ClassroomResponse(BaseModel):
    id: int
    number: str
    building: str
    capacity: int
    has_projector: bool
    has_virtual_board: bool
    has_camera: bool
    has_ac: bool

    model_config = {"from_attributes": True}


# ── Bookings ──────────────────────────────────────────────────────────────────

def _check_5min(v: datetime) -> datetime:
    if v.minute % 5 != 0 or v.second != 0 or v.microsecond != 0:
        raise ValueError(
            "Booking times must fall on 5-minute boundaries "
            "(minutes divisible by 5, seconds and microseconds must be 0)"
        )
    return v


class BookingCreate(BaseModel):
    classroom_id: int
    title: str
    description: str = ""
    start_time: datetime
    end_time: datetime
    booking_type: BookingType = BookingType.regular

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_granularity(cls, v: datetime) -> datetime:
        return _check_5min(v)

    @model_validator(mode="after")
    def validate_range(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class BookingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    booking_type: Optional[BookingType] = None

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_granularity(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            return _check_5min(v)
        return v


class BookingResponse(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    user_id: int
    classroom_id: int
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    booking_type: BookingType

    model_config = {"from_attributes": True}


# ── Smart suggestion ──────────────────────────────────────────────────────────

class SuggestionRequest(BaseModel):
    min_capacity: int
    start_time: datetime
    end_time: datetime
    requires_projector: bool = False
    requires_virtual_board: bool = False
    requires_camera: bool = False
    requires_ac: bool = False

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_granularity(cls, v: datetime) -> datetime:
        return _check_5min(v)

    @model_validator(mode="after")
    def validate_range(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class SuggestionResponse(BaseModel):
    full_matches: list[ClassroomResponse]
    partial_matches: list[ClassroomResponse]
