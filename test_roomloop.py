import sqlite3
import pytest
from roomloop.store import init_db
from roomloop.core import (create_single, create_recurring, cancel_booking,
                           cancel_series, availability, ConflictError)

TZ_BER, TZ_DEN = "Europe/Berlin", "America/Denver"


@pytest.fixture
def db():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_db(c)
    for rid, n, cap in [(3, "Aurora", 8), (4, "Basalt", 4),
                        (9, "Cinder", 12), (17, "Dune", 6)]:
        c.execute("INSERT INTO rooms VALUES (?,?,?)", (rid, n, cap))
    c.commit()
    yield c
    c.close()


def test_back_to_back_ok(db):
    create_single(db, 3, "2026-07-02T09:00:00", "2026-07-02T10:00:00",
                  "a", TZ_BER)
    create_single(db, 3, "2026-07-02T10:00:00", "2026-07-02T11:00:00",
                  "b", TZ_BER)


def test_overlap_conflicts(db):
    create_single(db, 3, "2026-07-02T09:00:00", "2026-07-02T10:00:00",
                  "a", TZ_BER)
    with pytest.raises(ConflictError):
        create_single(db, 3, "2026-07-02T09:30:00", "2026-07-02T10:30:00",
                      "b", TZ_BER)


def test_same_time_different_room_ok(db):
    create_single(db, 3, "2026-07-02T09:00:00", "2026-07-02T10:00:00",
                  "a", TZ_BER)
    create_single(db, 4, "2026-07-02T09:00:00", "2026-07-02T10:00:00",
                  "b", TZ_BER)


def test_recurring_skips_one_or_two(db):
    create_single(db, 3, "2026-07-13T09:00:00", "2026-07-13T10:00:00",
                  "x", TZ_BER)
    res = create_recurring(db, 3, "2026-07-06T09:00:00",
                           "2026-07-06T10:00:00", "u", "2026-07-27",
                           TZ_BER)
    assert len(res["rows"]) == 3 and len(res["skipped"]) == 1


def test_recurring_aborts_on_three_plus(db):
    for d in ["2026-07-06", "2026-07-13", "2026-07-20"]:
        create_single(db, 3, f"{d}T09:00:00", f"{d}T10:00:00", "x", TZ_BER)
    n0 = db.execute("SELECT COUNT(*) c FROM bookings").fetchone()["c"]
    with pytest.raises(ConflictError):
        create_recurring(db, 3, "2026-07-06T09:00:00",
                         "2026-07-06T10:00:00", "u", "2026-07-27",
                         TZ_BER)
    n1 = db.execute("SELECT COUNT(*) c FROM bookings").fetchone()["c"]
    assert n0 == n1


def test_cancel_series_keeps_past(db):
    res = create_recurring(db, 3, "2026-01-05T09:00:00",
                           "2026-01-05T10:00:00", "u", "2026-03-02",
                           TZ_BER)
    sid = res["series_id"]
    out = cancel_series(db, sid, now_utc="2026-02-01T00:00:00+00:00")
    assert out["cancelled"] and out["kept_past"]
    past = db.execute("SELECT status FROM bookings WHERE id=?",
                      (out["kept_past"][0],)).fetchone()["status"]
    assert past == "active"


def test_timestamps_stay_naive(db):
    b = create_single(db, 3, "2026-07-02T09:00:00", "2026-07-02T10:00:00",
                      "a", TZ_BER)
    assert b["start_local"] == "2026-07-02T09:00:00"
    assert "+" not in b["start_local"] and "Z" not in b["start_local"]


def test_denver_dst_wallclock(db):
    res = create_recurring(db, 9, "2026-03-02T09:00:00",
                           "2026-03-02T10:00:00", "u", "2026-03-16",
                           TZ_DEN)
    rows = sorted(res["rows"], key=lambda r: r["start_local"])
    assert [r["start_local"][11:16] for r in rows] == ["09:00"] * 3
    utc_hours = sorted(r["start_utc"][11:13] for r in rows)
    assert len(set(utc_hours)) == 2
    assert rows[0]["start_utc"][:13] != rows[2]["start_utc"][:13]


def test_availability_skips_gaps(db):
    free = availability(db, "2026-07-02T09:00:00", "2026-07-02T10:00:00",
                        TZ_BER)
    assert sorted(r["id"] for r in free) == [3, 4, 9, 17]
    create_single(db, 9, "2026-07-02T09:00:00", "2026-07-02T10:00:00",
                  "a", TZ_BER)
    free = availability(db, "2026-07-02T09:00:00", "2026-07-02T10:00:00",
                        TZ_BER)
    assert 9 not in [r["id"] for r in free]


def test_cancel_single(db):
    b = create_single(db, 4, "2026-07-02T09:00:00", "2026-07-02T10:00:00",
                      "a", TZ_BER)
    cancel_booking(db, b["id"])
    create_single(db, 4, "2026-07-02T09:00:00", "2026-07-02T10:00:00",
                  "b", TZ_BER)
