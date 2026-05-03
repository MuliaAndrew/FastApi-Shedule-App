from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # must run before app.database is imported so DATABASE_URL is set

# pylint: disable=wrong-import-position
from fastapi import FastAPI

from app.database import Base, engine
from app.routers import auth, bookings, classrooms, users


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Classroom Booking Service", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(classrooms.router)
app.include_router(bookings.router)
