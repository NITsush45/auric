# DECISIONS.md

1. **(a) REST over CLI** — reporting parser + `GET /rooms` dashboard already assume HTTP; CLI would break integrations, so REST preserves them.
2. **(a) R1 vs R2 resolved by count** — brief demands both all-or-nothing and skip-1-or-2: 1–2 clashes → skip those, rest 201; ≥3 clashes → 409 with nothing saved.
3. **(a) Dual timestamps** — `start_local` naive ISO is stored/returned (C1 compat); hidden `start_utc` drives conflict math and is never exposed.
4. **(a) Wall-clock recurrence** — naive `+7 days` then per-date tz→UTC; fixes Denver 1-hour DST bug the manager mentioned.
5. **(a) Real room IDs, not 1..N** — C2 sample (3,4,9,17) contradicts R5; availability iterates DB IDs, treating R5 as stale wiki advice.
6. **(a) One-call series cancel** — `DELETE /series/<id>` cancels future, keeps past (soft-delete `status` retains audit); fixes "busy forever" complaint.
7. **(b) Confirm clash threshold + "local" meaning** — is 1–2 skip / ≥3 abort right, and is reporting-local the room's or booker's tz?
8. **(b) Confirm retention + limits** — max series length, past-booking window, and hard-delete policy for cancelled rows?
9. **(c) AI helped with boilerplate, corrected 3x** — generated handler/test skeletons; corrected offset-aware ISO (breaks C1), naive-UTC compare (breaks DST), and `range(1,N+1)` room iteration (breaks gaps). FastAPI layer kept thin over the tested core so Swagger stays in sync.
10. **(d) Left out / next** — no auth (internal tool), no pagination, no move/update endpoint, no per-room tz; next: auth, paged lists, Dockerfile/CI.

