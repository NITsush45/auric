# RoomLoop Booking Service

FastAPI REST API + booking core (`roomloop/`). Interactive docs (Swagger UI) at `/docs` — no separate frontend needed.

## Run

```bash
pip install -r requirements.txt
python seed.py
python -m uvicorn app:app --port 8000
python -m pytest test_roomloop.py -v
```

Then open http://127.0.0.1:8000/docs to demo and test every endpoint.

## Why REST (not CLI)

Other tools already consume the API (`GET /rooms`, timestamp parsing in the
reporting job), so a REST service preserves those integrations; a CLI would
break them.

## API

| Method | Path | Body / Query |
|---|---|---|
| GET | `/rooms` | — |
| POST | `/rooms` | `{id, name, capacity?}` |
| POST | `/bookings` | `{room_id, start, end, user, timezone?}` |
| POST | `/bookings/recurring` | same + `{repeat_until: YYYY-MM-DD}` |
| DELETE | `/bookings/<id>` | — |
| DELETE | `/series/<sid>?now=<UTC-ISO>` | — |
| GET | `/bookings?room_id=&status=&series_id=` | — |
| GET | `/availability?start=&end=&timezone=` | — |

Timestamps in/out are **naive local ISO** (`2026-07-02T09:00:00`, C1).
`timezone` is IANA (`Europe/Berlin`, `America/Denver`), default Berlin.

## Key semantics

- **R1 vs R2:** 1–2 clashing instances are skipped (rest created); ≥3
  clashes → `409` and nothing saved.
- **R3:** weekly repeats keep wall-clock time; UTC per occurrence (DST-safe).
- **R4:** overlap = `a.start < b.end and b.start < a.end` (back-to-back OK).
- **Cancel series:** one `DELETE /series/<id>` cancels all future, keeps past.
- **Availability:** iterates real room IDs (3,4,9,17), never blind 1..N.
