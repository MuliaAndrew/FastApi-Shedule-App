# Classroom Booking Service

REST API for booking university classrooms, built with FastAPI and SQLite.

## Features

- Full CRUD for classrooms and bookings
- JWT-based authentication for admins and editors
- Role-based access control: **admin**, **editor**, **reader**
- 5-minute time granularity enforcement on all bookings
- Overlap detection prevents double-booking
- Smart suggestion endpoint finds the best available classroom for given requirements

## Requirements

- Python 3.12+
- Dependencies listed in `requirements.txt`

## Setup

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The SQLite database file (`schedule.db`) is created automatically on first run.

Interactive API docs are available at `http://localhost:8000/docs`.

## Roles

| Role | How to obtain | Capabilities |
|---|---|---|
| **admin** | First registered user | Full access: manage classrooms, all bookings, add editors |
| **editor** | Added by admin via `POST /users/editors` | Create, update, delete own bookings; use smart suggest |
| **reader** | Anyone (register via `POST /auth/register`) | Read-only: classrooms, editors list, booking schedules |

Public endpoints (no token required): classroom list, editor list, classroom schedule, editor schedule.

## Authentication

Admin and editor requests require a Bearer token obtained from `POST /auth/login`.

```
Authorization: Bearer <token>
```

## API Reference

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | — | Register a new reader account (first user becomes admin) |
| POST | `/auth/login` | — | Login; returns JWT access token |

### Users

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users/editors` | — | List all editors |
| POST | `/users/editors` | admin | Create an editor account |

### Classrooms

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/classrooms` | — | List all classrooms |
| GET | `/classrooms/{id}` | — | Get a single classroom |
| POST | `/classrooms` | admin | Create a classroom |
| PATCH | `/classrooms/{id}` | admin | Update a classroom |
| DELETE | `/classrooms/{id}` | admin | Delete a classroom |

Classroom fields: `number`, `building`, `capacity`, `has_projector`, `has_virtual_board`, `has_camera`, `has_ac`.

### Bookings

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/bookings/classroom/{id}` | — | Schedule for a classroom |
| GET | `/bookings/editor/{id}` | — | All bookings made by an editor |
| GET | `/bookings/{id}` | — | Get a single booking |
| POST | `/bookings` | editor/admin | Create a booking |
| PATCH | `/bookings/{id}` | editor/admin | Update a booking (editors: own only) |
| DELETE | `/bookings/{id}` | editor/admin | Delete a booking (editors: own only) |
| POST | `/bookings/suggest` | editor/admin | Find available classrooms matching requirements |

#### Booking types

- `regular` — standard lecture or class
- `maintenance` — technical work
- `non_working` — closed period (night, holidays, large events)

#### Time granularity

All `start_time` and `end_time` values must fall on 5-minute boundaries — minutes must be divisible by 5, seconds and microseconds must be zero. Requests with invalid granularity are rejected with HTTP 422.

#### UID invariant

Booking IDs are autoincremented. A booking created later always has a strictly larger ID than any previously created booking.

### Smart Suggestion

`POST /bookings/suggest` accepts requirements and returns available classrooms ranked by fit.

**Request body:**

```json
{
  "min_capacity": 25,
  "start_time": "2024-09-01T10:00:00",
  "end_time": "2024-09-01T12:00:00",
  "requires_projector": true,
  "requires_virtual_board": false,
  "requires_camera": false,
  "requires_ac": true
}
```

**Response:**

```json
{
  "full_matches": [...],
  "partial_matches": [...]
}
```

- `full_matches` — up to 10 classrooms that are free during the requested interval and satisfy all requirements.
- `partial_matches` — up to 10 classrooms sorted by best fit score (capacity match weighted higher than individual features), returned only when `full_matches` is empty.

## Running Tests

```bash
pytest tests/ -v
```

32 tests cover authentication, classroom CRUD, booking CRUD, overlap detection, time granularity validation, role enforcement, and the smart suggestion endpoint.
