"""Value formats for structured data, and the one place a stored date becomes a timestamp.

The formats are the ones named in packages/site/jsonld-rules.json ("formats"), read from Google's
documentation. Content stores a day (YYYY-MM-DD) or a day and minute (YYYY-MM-DDTHH:MM); only
`timestamp` turns it into the full ISO 8601 value with the site's offset, so a date written by hand
never reaches a JSON-LD field, and a date without its timezone is a build error, not a Search
Console warning a month later.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Callable
from urllib.parse import urlparse

from ..errors import BuildError

_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_PARTIAL_DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
_LOCAL_MINUTE = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})$")
_TIMESTAMP = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|[+-](\d{2}):(\d{2}))$")
_LOCAL_DATETIME = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})(:\d{2})?(Z|[+-]\d{2}:\d{2})?$")
_TIME = re.compile(r"^(\d{2}):(\d{2}):(\d{2})$")
_DURATION = re.compile(r"^P(?!$)(\d+Y)?(\d+M)?(\d+W)?(\d+D)?(T(?=\d)(\d+H)?(\d+M)?(\d+(\.\d+)?S)?)?$")
_PHONE = re.compile(r"^\+\d{1,3}[\d ()\-]{6,}$")
_COUNTRY = re.compile(r"^[A-Z]{2}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TAG = re.compile(r"</?[A-Za-z][^>]*>")
_DAYS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}


def _valid_day(text: str) -> bool:
    match = _DATE.match(text)
    if not match:
        return False
    try:
        date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return False
    return True


def is_date(value: Any) -> bool:
    return isinstance(value, str) and _valid_day(value)


def is_partial_date(value: Any) -> bool:
    """A year, a month or a day: the forms ISO 8601 allows for foundingDate."""
    if not isinstance(value, str) or not _PARTIAL_DATE.match(value):
        return False
    return len(value) < 10 or _valid_day(value)


def _clock(hour: str, minute: str, second: str = "00") -> bool:
    return int(hour) < 24 and int(minute) < 60 and int(second) < 60


def is_datetime(value: Any) -> bool:
    """A full ISO 8601 timestamp that carries its timezone (an offset or Z)."""
    if not isinstance(value, str):
        return False
    match = _TIMESTAMP.match(value)
    if not match or not _valid_day(match.group(1)) or not _clock(*match.group(2, 3, 4)):
        return False
    return match.group(7) is None or (int(match.group(7)) < 24 and int(match.group(8)) < 60)


def is_datetime_or_date(value: Any) -> bool:
    """Event dates: a day when the hour is unknown, else a local date and time (the offset is optional)."""
    if is_date(value):
        return True
    if not isinstance(value, str):
        return False
    match = _LOCAL_DATETIME.match(value)
    return bool(match) and _valid_day(match.group(1)) and _clock(*match.group(2, 3))


def is_time(value: Any) -> bool:
    return isinstance(value, str) and bool((m := _TIME.match(value)) and _clock(*m.groups()))


def is_duration(value: Any) -> bool:
    return isinstance(value, str) and bool(_DURATION.match(value))


def is_url(value: Any) -> bool:
    if not isinstance(value, str) or " " in value:
        return False
    parts = urlparse(value)
    return parts.scheme == "https" and bool(parts.netloc)


def is_phone(value: Any) -> bool:
    return isinstance(value, str) and bool(_PHONE.match(value)) and sum(c.isdigit() for c in value) >= 10


def is_email(value: Any) -> bool:
    return isinstance(value, str) and bool(_EMAIL.match(value))


def is_country(value: Any) -> bool:
    return isinstance(value, str) and bool(_COUNTRY.match(value))


def is_day_of_week(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return value.removeprefix("https://schema.org/") in _DAYS


def is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not _TAG.search(value)


# format name (jsonld-rules.json "formats") -> checker
CHECKS: dict[str, Callable[[Any], bool]] = {
    "datetime": is_datetime, "datetime-or-date": is_datetime_or_date, "date": is_date, "date-partial": is_partial_date,
    "time": is_time, "duration": is_duration, "url": is_url, "phone": is_phone, "email": is_email, "country": is_country,
    "day-of-week": is_day_of_week, "text": is_text,
}


def check_format(fmt: str, value: Any) -> bool:
    try:
        return CHECKS[fmt](value)
    except KeyError:
        raise BuildError(f"jsonld-rules.json names an unknown format {fmt!r}; known: {', '.join(sorted(CHECKS))}") from None


def is_stored_day(value: Any) -> bool:
    """What content files may hold: a day, or a day and minute."""
    if is_date(value):
        return True
    match = _LOCAL_MINUTE.match(value) if isinstance(value, str) else None
    return bool(match) and _valid_day(match.group(1)) and _clock(match.group(2), match.group(3))


def clock_time(stored: str) -> str:
    """A time of day as Google wants it (hh:mm:ss) from how a person writes it (07:00 or 07:00:00)."""
    match = re.match(r"^(\d{2}):(\d{2})(?::(\d{2}))?$", stored) if isinstance(stored, str) else None
    if not match or not _clock(match.group(1), match.group(2), match.group(3) or "00"):
        raise BuildError(f"{stored!r} is not a time of day: write HH:MM")
    return f"{match.group(1)}:{match.group(2)}:{match.group(3) or '00'}"


def timestamp(stored: str, dates: dict[str, str]) -> str:
    """A stored day (or day and minute) as a full timestamp in the site's timezone.

    `dates` is "dates" in site.json: the offset, and the time used when only the day is known."""
    if not is_stored_day(stored):
        raise BuildError(f"{stored!r} is not a date: write YYYY-MM-DD, or YYYY-MM-DDTHH:MM")
    if "T" in stored:
        return f"{stored}:00{dates['offset']}"
    return f"{stored}T{dates['timeOfDay']}{dates['offset']}"
