from functools import cache
from zoneinfo import available_timezones

from django.core.exceptions import ValidationError


@cache
def _timezone_names():
    """Return the IANA time zone names, read once per process."""
    return frozenset(available_timezones())


def validate_timezone(value):
    """Reject values that are not IANA time zone names, such as "Europe/Berlin"."""
    if value not in _timezone_names():
        raise ValidationError(
            "%(value)s is not a valid time zone.",
            code="invalid_timezone",
            params={"value": value},
        )
