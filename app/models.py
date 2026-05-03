import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, enum.Enum):
    # pylint: disable=invalid-name
    admin = "admin"
    editor = "editor"
    reader = "reader"


class BookingType(str, enum.Enum):
    # pylint: disable=invalid-name
    regular = "regular"
    maintenance = "maintenance"
    non_working = "non_working"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.reader)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    bookings = relationship("Booking", back_populates="creator")


class Classroom(Base):
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    number = Column(String(20), nullable=False)
    building = Column(String(100), nullable=False)
    capacity = Column(Integer, nullable=False)
    has_projector = Column(Boolean, default=False, nullable=False)
    has_virtual_board = Column(Boolean, default=False, nullable=False)
    has_camera = Column(Boolean, default=False, nullable=False)
    has_ac = Column(Boolean, default=False, nullable=False)

    bookings = relationship("Booking", back_populates="classroom")


class Booking(Base):
    __tablename__ = "bookings"

    # autoincrement PK satisfies the uid invariant:
    # a booking created later always gets a strictly larger id
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="", nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    booking_type = Column(
        SAEnum(BookingType), nullable=False, default=BookingType.regular
    )

    creator = relationship("User", back_populates="bookings")
    classroom = relationship("Classroom", back_populates="bookings")
