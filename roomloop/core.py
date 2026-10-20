import uuid
from datetime import timedelta
from .timeutil import parse_naive, to_utc_iso, now_utc_iso, DEFAULT_TZ


class ConflictError(Exception):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or []


def row_public(r):
    return {"id": r["id"], "room_id": r["room_id"], "user": r["user_name"],
            "series_id": r["series_id"], "start": r["start_local"],
            "end": r["end_local"], "timezone": r["timezone"],
            "status": r["status"]}


def find_conflicts(conn, room_id, start_utc, end_utc, exclude_id=None):
    q = ("SELECT * FROM bookings WHERE room_id=? AND status='active'"
         " AND start_utc < ? AND end_utc > ?")
    args = [room_id, end_utc, start_utc]
    if exclude_id is not None:
        q += " AND id != ?"
        args.append(exclude_id)
    return conn.execute(q, args).fetchall()


def create_single(conn, room_id, start_s, end_s, user, tz=DEFAULT_TZ):
    room = conn.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not room:
        raise ValueError(f"room {room_id} does not exist")
    s, e = parse_naive(start_s), parse_naive(end_s)
    if not s < e:
        raise ValueError("end must be after start")
    su, eu = to_utc_iso(s, tz), to_utc_iso(e, tz)
    cl = find_conflicts(conn, room_id, su, eu)
    if cl:
        raise ConflictError("conflict with existing booking(s)",
                            [{"id": c["id"]} for c in cl])
    cur = conn.execute(
        "INSERT INTO bookings (room_id,user_name,series_id,start_local,"
        "end_local,start_utc,end_utc,timezone,status,created_at)"
        " VALUES (?,?,NULL,?,?,?,?,?, 'active', ?)",
        (room_id, user, s.isoformat(), e.isoformat(), su, eu, tz,
         now_utc_iso()))
    conn.commit()
    return conn.execute("SELECT * FROM bookings WHERE id=?",
                        (cur.lastrowid,)).fetchone()


def create_recurring(conn, room_id, start_s, end_s, user, until_s,
                     tz=DEFAULT_TZ, max_occ=500):
    room = conn.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not room:
        raise ValueError(f"room {room_id} does not exist")
    s0, e0 = parse_naive(start_s), parse_naive(end_s)
    if not s0 < e0:
        raise ValueError("end must be after start")
    try:
        until = parse_naive(until_s).date() if "T" in until_s else \
            parse_naive(until_s + "T00:00:00").date()
    except ValueError:
        raise ValueError("repeat_until must be YYYY-MM-DD")
    if until < s0.date():
        raise ValueError("repeat_until is before start")
    dur = e0 - s0
    occ, k = [], 0
    while True:
        sk = s0 + timedelta(weeks=k)
        if sk.date() > until:
            break
        occ.append((sk, sk + dur))
        k += 1
        if len(occ) > max_occ:
            raise ValueError("series too long; narrow repeat_until")
    checks = []
    for sk, ek in occ:
        su, eu = to_utc_iso(sk, tz), to_utc_iso(ek, tz)
        cl = find_conflicts(conn, room_id, su, eu)
        checks.append((sk, ek, su, eu, [c["id"] for c in cl]))
    bad = [c for c in checks if c[4]]
    if len(bad) >= 3:
        raise ConflictError(
            f"series blocked: {len(bad)} clash (>=3, aborting all)",
            [{"start_local": sk.isoformat(), "conflicts_with": w}
             for sk, ek, su, eu, w in bad])
    sid = uuid.uuid4().hex[:12]
    created, skipped = [], []
    for sk, ek, su, eu, w in checks:
        if w:
            skipped.append({"start_local": sk.isoformat(),
                            "conflicts_with": w})
            continue
        cur = conn.execute(
            "INSERT INTO bookings (room_id,user_name,series_id,start_local,"
            "end_local,start_utc,end_utc,timezone,status,created_at)"
            " VALUES (?,?,?,?,?,?,?,?, 'active', ?)",
            (room_id, user, sid, sk.isoformat(), ek.isoformat(),
             su, eu, tz, now_utc_iso()))
        created.append(cur.lastrowid)
    conn.commit()
    rows = [conn.execute("SELECT * FROM bookings WHERE id=?", (i,)).fetchone()
            for i in created]
    return {"series_id": sid, "rows": rows, "skipped": skipped}


def cancel_booking(conn, bid):
    b = conn.execute("SELECT * FROM bookings WHERE id=?", (bid,)).fetchone()
    if not b or b["status"] != "active":
        raise KeyError(f"booking {bid} not found/active")
    conn.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (bid,))
    conn.commit()
    return True


def cancel_series(conn, sid, now_utc=None):
    now_utc = now_utc or now_utc_iso()
    rows = conn.execute("SELECT * FROM bookings WHERE series_id=? AND "
                        "status='active'", (sid,)).fetchall()
    if not rows:
        raise KeyError(f"series {sid} not found/active")
    cancelled, kept = [], []
    for r in rows:
        if r["end_utc"] <= now_utc:
            kept.append(r["id"])
        else:
            conn.execute("UPDATE bookings SET status='cancelled' WHERE id=?",
                         (r["id"],))
            cancelled.append(r["id"])
    conn.commit()
    return {"series_id": sid, "cancelled": cancelled, "kept_past": kept,
            "now_utc": now_utc}


def availability(conn, start_s, end_s, tz=DEFAULT_TZ):
    su = to_utc_iso(parse_naive(start_s), tz)
    eu = to_utc_iso(parse_naive(end_s), tz)
    free = []
    for r in conn.execute("SELECT * FROM rooms ORDER BY id").fetchall():
        if not find_conflicts(conn, r["id"], su, eu):
            free.append(dict(r))
    return free
