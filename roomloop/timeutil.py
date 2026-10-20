from datetime import datetime, timezone, timedelta


def _last_sunday(year, month):
    d = datetime(year, month, 31)
    while d.weekday() != 6:
        d -= timedelta(days=1)
    return d.date()


def _nth_sunday(year, month, n):
    d = datetime(year, month, 1)
    while d.weekday() != 6:
        d += timedelta(days=1)
    return (d + timedelta(weeks=n - 1)).date()


def _berlin_offset(naive):
    s = _last_sunday(naive.year, 3)
    e = _last_sunday(naive.year, 10)
    dst = s <= naive.date() < e or (
        naive.date() == s and naive.hour >= 2) or (
        naive.date() == e and naive.hour < 3)
    return timedelta(hours=2 if dst else 1)


def _denver_offset(naive):
    s = _nth_sunday(naive.year, 3, 2)
    e = _nth_sunday(naive.year, 11, 1)
    dst = s <= naive.date() < e or (
        naive.date() == s and naive.hour >= 2) or (
        naive.date() == e and naive.hour < 2)
    return timedelta(hours=-6 if dst else -7)


_OFFSETS = {"Europe/Berlin": _berlin_offset, "America/Denver": _denver_offset}
DEFAULT_TZ = "Europe/Berlin"


def parse_naive(s):
    return datetime.fromisoformat(s)


def to_utc_iso(naive_local, tz_name):
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name)
        return naive_local.replace(tzinfo=tz).astimezone(
            timezone.utc).isoformat()
    except Exception:
        pass
    fn = _OFFSETS.get(tz_name)
    if fn is None:
        raise ValueError(f"unknown timezone {tz_name!r}")
    return (naive_local - fn(naive_local)).replace(
        tzinfo=timezone.utc).isoformat()


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


def overlaps(a_s, a_e, b_s, b_e):
    return a_s < b_e and b_s < a_e
