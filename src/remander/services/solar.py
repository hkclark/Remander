"""Solar service — sunrise/sunset calculation and dynamic bitmask generation."""

import datetime as dt
import zoneinfo

from astral import LocationInfo
from astral.sun import sun


async def get_sunrise_sunset(
    latitude: float,
    longitude: float,
    timezone: str = "UTC",
    date: dt.date | None = None,
) -> tuple[dt.datetime, dt.datetime]:
    """Return (sunrise, sunset) datetimes in local time for the given location and date.

    The `timezone` parameter controls the local timezone for the returned datetimes.
    Defaults to UTC if not provided. Defaults to today if no date is provided.
    """
    if date is None:
        date = dt.date.today()

    location = LocationInfo(latitude=latitude, longitude=longitude)
    s = sun(location.observer, date=date)
    tz = zoneinfo.ZoneInfo(timezone)
    return s["sunrise"].astimezone(tz), s["sunset"].astimezone(tz)


def _round_to_hour(time: dt.datetime) -> int:
    """Round a datetime to the nearest hour (0-23)."""
    if time.minute >= 30:
        return (time.hour + 1) % 24
    return time.hour


def compute_dynamic_bitmask(
    sunrise: dt.datetime,
    sunset: dt.datetime,
    sunrise_offset_minutes: int = 0,
    sunset_offset_minutes: int = 0,
    fill_value: str = "1",
) -> str:
    """Build a 24-char hour bitmask from sunrise/sunset times.

    Hours between the (offset-adjusted, rounded) sunrise and sunset are filled
    with `fill_value`; all other hours get the opposite value. Handles midnight
    crossings (when sunrise_hour > sunset_hour).
    """
    adj_sunrise = sunrise + dt.timedelta(minutes=sunrise_offset_minutes)
    adj_sunset = sunset + dt.timedelta(minutes=sunset_offset_minutes)

    sunrise_hour = _round_to_hour(adj_sunrise)
    sunset_hour = _round_to_hour(adj_sunset)

    opposite = "0" if fill_value == "1" else "1"

    # When both round to the same hour, disambiguate by checking the actual time gap
    if sunrise_hour == sunset_hour:
        gap_hours = (adj_sunset - adj_sunrise).total_seconds() / 3600
        return fill_value * 24 if gap_hours > 12 else opposite * 24

    bitmask = []
    for h in range(24):
        if sunrise_hour < sunset_hour:
            # Normal: sunrise and sunset on the same day
            bitmask.append(fill_value if sunrise_hour <= h < sunset_hour else opposite)
        else:
            # Wrapping: sunset crosses midnight
            bitmask.append(fill_value if h >= sunrise_hour or h < sunset_hour else opposite)

    return "".join(bitmask)
