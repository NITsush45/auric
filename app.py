from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from roomloop.store import get_conn, init_db, DB_PATH
from roomloop.core import (create_single, create_recurring, cancel_booking,
                           cancel_series, availability, ConflictError,
                           row_public)
from roomloop.timeutil import DEFAULT_TZ

app = FastAPI(title="RoomLoop Booking Service",
              description="Meeting-room booking core. Timestamps are naive "
                          "local ISO (2026-07-02T09:00:00).",
              version="1.0")

NAIVE_EX = "2026-07-02T09:00:00"


class RoomIn(BaseModel):
    id: int = Field(examples=[3])
    name: str = Field(examples=["Aurora"])
    capacity: int = 4


class Room(RoomIn):
    pass


class BookingIn(BaseModel):
    room_id: int = Field(examples=[3])
    start: str = Field(examples=[NAIVE_EX])
    end: str = Field(examples=["2026-07-02T10:00:00"])
    user: str = Field(examples=["alice"])
    timezone: str = Field(default=DEFAULT_TZ,
                          examples=["Europe/Berlin"])


class RecurringIn(BookingIn):
    repeat_until: str = Field(examples=["2026-08-31"])


class Booking(BaseModel):
    id: int
    room_id: int
    user: str
    series_id: Optional[str] = None
    start: str
    end: str
    timezone: str
    status: str


class RecurringOut(BaseModel):
    series_id: str
    created: List[Booking]
    skipped: list


def conn():
    c = get_conn(DB_PATH)
    init_db(c)
    return c


def http409(e: ConflictError):
    raise HTTPException(status_code=409,
                        detail={"error": str(e), "conflicts": e.details})


@app.get("/", tags=["meta"])
def root():
    return {"service": "RoomLoop", "docs": "/docs"}


@app.get("/rooms", response_model=List[Room], tags=["rooms"],
         summary="List rooms (C2 sample shape)")
def list_rooms():
    c = conn()
    try:
        return [dict(r) for r in
                c.execute("SELECT * FROM rooms ORDER BY id").fetchall()]
    finally:
        c.close()


@app.post("/rooms", response_model=Room, status_code=201, tags=["rooms"])
def upsert_room(r: RoomIn):
    c = conn()
    try:
        c.execute("INSERT OR REPLACE INTO rooms VALUES (?,?,?)",
                  (r.id, r.name, r.capacity))
        c.commit()
        return dict(c.execute("SELECT * FROM rooms WHERE id=?",
                              (r.id,)).fetchone())
    finally:
        c.close()


@app.post("/bookings", response_model=Booking, status_code=201,
          tags=["bookings"], summary="Create a single booking")
def post_booking(b: BookingIn):
    c = conn()
    try:
        try:
            row = create_single(c, b.room_id, b.start, b.end, b.user,
                                b.timezone)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ConflictError as e:
            http409(e)
        return row_public(row)
    finally:
        c.close()


@app.post("/bookings/recurring", response_model=RecurringOut,
          status_code=201, tags=["bookings"],
          summary="Create weekly series (R1/R2/R3)")
def post_recurring(b: RecurringIn):
    c = conn()
    try:
        try:
            res = create_recurring(c, b.room_id, b.start, b.end, b.user,
                                   b.repeat_until, b.timezone)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ConflictError as e:
            http409(e)
        return {"series_id": res["series_id"],
                "created": [row_public(r) for r in res["rows"]],
                "skipped": res["skipped"]}
    finally:
        c.close()


@app.get("/bookings", response_model=List[Booking], tags=["bookings"])
def list_bookings(room_id: Optional[int] = None,
                  status: str = "active",
                  series_id: Optional[str] = None):
    c = conn()
    try:
        q, a = "SELECT * FROM bookings WHERE status=?", [status]
        if room_id is not None:
            q += " AND room_id=?"; a.append(room_id)
        if series_id:
            q += " AND series_id=?"; a.append(series_id)
        q += " ORDER BY start_utc"
        return [row_public(r) for r in c.execute(q, a).fetchall()]
    finally:
        c.close()


@app.delete("/bookings/{bid}", tags=["bookings"])
def delete_booking(bid: int):
    c = conn()
    try:
        try:
            cancel_booking(c, bid)
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=404, detail=str(e))
        return {"cancelled": bid}
    finally:
        c.close()


@app.delete("/series/{sid}", tags=["bookings"],
            summary="Cancel whole series future (keeps past)")
def delete_series(sid: str, now: Optional[str] = None):
    c = conn()
    try:
        try:
            return cancel_series(c, sid, now)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
    finally:
        c.close()


@app.get("/availability", response_model=List[Room], tags=["rooms"],
         summary="Free rooms (iterates real IDs, not 1..N)")
def get_availability(
        start: str = Query(examples=[NAIVE_EX]),
        end: str = Query(examples=["2026-07-02T10:00:00"]),
        timezone: str = Query(default=DEFAULT_TZ)):
    c = conn()
    try:
        return availability(c, start, end, timezone)
    finally:
        c.close()
