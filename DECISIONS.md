# DECISIONS.md (10 bullets)

1. **REST over CLI (a)** — reporting parser + `GET /rooms` dashboard already assume HTTP; CLI would break integrations, so REST preserves them.
2. **R1 vs R2 resolved by count (a)** — brief demands both all-or-nothing and skip-1-or-2: 1–2 clashes → skip those, rest 201; ≥3 clashes → 409 with nothing saved.
3. **Dual timestamps (a)** — `start_local` naive ISO is stored/returned (C1 compat); hidden `start_utc` drives conflict math and is never exposed.
4. **Wall-clock recurrence (a)** — naive `+7 days` then per-date tz→UTC; fixes Denver 1-hour DST bug the manager mentioned.
5. **Real room IDs, not 1..N (a)** — C2 sample (3,4,9,17) contradicts R5; availability iterates DB IDs, treating R5 as stale wiki advice.
6. **One-call series cancel (a)** — `DELETE /series/<id>` cancels future, keeps past (soft-delete `status` retains audit); fixes "busy forever" complaint.
7. **Confirm clash threshold + "local" meaning (b)** — is 1–2 skip / ≥3 abort right, and is reporting-local the room's or booker's tz?
8. **Confirm retention + limits (b)** — max series length, past-booking window, and hard-delete policy for cancelled rows?
9. **AI helped with boilerplate, corrected 3× (c)** — it suggested offset-aware ISO (breaks C1), naive-UTC compare (breaks DST), `range(1,N+1)` rooms (breaks gaps); all fixed. FastAPI layer added per mentor steer; booking core + tests untouched.
10. **Left out / next (d)** — no auth (internal tool), no pagination, no move/update endpoint, no per-room tz; next: auth, paged lists, OpenAPI.
