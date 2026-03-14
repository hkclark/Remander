"""Tests for the solar (sunrise/sunset) service — RED phase (TDD)."""

from datetime import datetime, timezone

from remander.services.solar import compute_dynamic_bitmask, get_sunrise_sunset


class TestGetSunriseSunset:
    async def test_known_location_and_date(self) -> None:
        """NYC on June 21 (summer solstice) — sunrise ~9:25 UTC, sunset ~00:30 UTC next day."""
        from datetime import date

        sunrise, sunset = await get_sunrise_sunset(40.7128, -74.0060, date=date(2026, 6, 21))

        # Sunrise should be around 9:00-10:00 UTC for NYC in summer
        assert 9 <= sunrise.hour <= 10
        # Sunset should be around 0:00-1:00 UTC (next day) for NYC in summer
        assert 0 <= sunset.hour <= 1

    async def test_defaults_to_today(self) -> None:
        """Should work without a date (defaults to today)."""
        sunrise, sunset = await get_sunrise_sunset(40.7128, -74.0060)
        assert sunrise is not None
        assert sunset is not None

    async def test_local_timezone_returns_local_hours(self) -> None:
        """With timezone='America/New_York', returned hours should be local (EDT = UTC-4 in June)."""
        from datetime import date

        sunrise, sunset = await get_sunrise_sunset(
            40.7128, -74.0060, timezone="America/New_York", date=date(2026, 6, 21)
        )
        # NYC EDT sunrise in June is around 5:00-6:00 AM local time
        assert 5 <= sunrise.hour <= 6
        # NYC EDT sunset in June is around 8:00-9:00 PM (20:00-21:00) local time
        assert 20 <= sunset.hour <= 21

    async def test_utc_timezone_matches_default(self) -> None:
        """timezone='UTC' should produce the same result as no timezone argument."""
        from datetime import date

        test_date = date(2026, 6, 21)
        sunrise_default, sunset_default = await get_sunrise_sunset(40.7128, -74.0060, date=test_date)
        sunrise_utc, sunset_utc = await get_sunrise_sunset(
            40.7128, -74.0060, timezone="UTC", date=test_date
        )
        assert sunrise_default.hour == sunrise_utc.hour
        assert sunset_default.hour == sunset_utc.hour


    async def test_does_not_fail_when_dusk_unavailable(self) -> None:
        """At lat=61°N on June 21, dusk can't be computed (midnight sun zone), but
        sunrise and sunset are valid.  get_sunrise_sunset() must not raise."""
        from datetime import date

        sunrise, sunset = await get_sunrise_sunset(61.0, 10.0, date=date(2026, 6, 21))
        # Sun rises before 2:00 UTC and sets after 20:00 UTC at this latitude
        assert sunrise.hour < 2
        assert sunset.hour >= 20


class TestComputeDynamicBitmask:
    def test_basic_daytime_bitmask(self) -> None:
        """Sunrise at 6:00, sunset at 20:00 -> hours 6-19 active."""
        sunrise = datetime(2026, 6, 21, 6, 0, tzinfo=timezone.utc)
        sunset = datetime(2026, 6, 21, 20, 0, tzinfo=timezone.utc)

        result = compute_dynamic_bitmask(sunrise, sunset, fill_value="1")
        #                 000000111111111111110000
        assert result == "000000111111111111110000"

    def test_nighttime_bitmask_fill_zero(self) -> None:
        """fill_value='0' means hours between sunrise and sunset are 0 (inactive)."""
        sunrise = datetime(2026, 6, 21, 6, 0, tzinfo=timezone.utc)
        sunset = datetime(2026, 6, 21, 20, 0, tzinfo=timezone.utc)

        result = compute_dynamic_bitmask(sunrise, sunset, fill_value="0")
        assert result == "111111000000000000001111"

    def test_positive_sunrise_offset(self) -> None:
        """Sunrise at 6:00 + 60min offset -> effective sunrise at 7:00."""
        sunrise = datetime(2026, 6, 21, 6, 0, tzinfo=timezone.utc)
        sunset = datetime(2026, 6, 21, 20, 0, tzinfo=timezone.utc)

        result = compute_dynamic_bitmask(sunrise, sunset, sunrise_offset_minutes=60, fill_value="1")
        assert result == "000000011111111111110000"

    def test_negative_sunrise_offset(self) -> None:
        """Sunrise at 6:00 - 60min offset -> effective sunrise at 5:00."""
        sunrise = datetime(2026, 6, 21, 6, 0, tzinfo=timezone.utc)
        sunset = datetime(2026, 6, 21, 20, 0, tzinfo=timezone.utc)

        result = compute_dynamic_bitmask(
            sunrise, sunset, sunrise_offset_minutes=-60, fill_value="1"
        )
        assert result == "000001111111111111110000"

    def test_positive_sunset_offset(self) -> None:
        """Sunset at 20:00 + 60min offset -> effective sunset at 21:00."""
        sunrise = datetime(2026, 6, 21, 6, 0, tzinfo=timezone.utc)
        sunset = datetime(2026, 6, 21, 20, 0, tzinfo=timezone.utc)

        result = compute_dynamic_bitmask(sunrise, sunset, sunset_offset_minutes=60, fill_value="1")
        assert result == "000000111111111111111000"

    def test_negative_sunset_offset(self) -> None:
        """Sunset at 20:00 - 60min offset -> effective sunset at 19:00."""
        sunrise = datetime(2026, 6, 21, 6, 0, tzinfo=timezone.utc)
        sunset = datetime(2026, 6, 21, 20, 0, tzinfo=timezone.utc)

        result = compute_dynamic_bitmask(sunrise, sunset, sunset_offset_minutes=-60, fill_value="1")
        assert result == "000000111111111111100000"

    def test_rounding_sunrise_up(self) -> None:
        """Sunrise at 6:35 rounds to 7."""
        sunrise = datetime(2026, 6, 21, 6, 35, tzinfo=timezone.utc)
        sunset = datetime(2026, 6, 21, 20, 0, tzinfo=timezone.utc)

        result = compute_dynamic_bitmask(sunrise, sunset, fill_value="1")
        assert result == "000000011111111111110000"

    def test_rounding_sunrise_down(self) -> None:
        """Sunrise at 6:20 rounds to 6."""
        sunrise = datetime(2026, 6, 21, 6, 20, tzinfo=timezone.utc)
        sunset = datetime(2026, 6, 21, 20, 0, tzinfo=timezone.utc)

        result = compute_dynamic_bitmask(sunrise, sunset, fill_value="1")
        assert result == "000000111111111111110000"

    def test_rounding_at_30_minutes_rounds_up(self) -> None:
        """Sunrise at exactly 6:30 rounds up to 7."""
        sunrise = datetime(2026, 6, 21, 6, 30, tzinfo=timezone.utc)
        sunset = datetime(2026, 6, 21, 20, 0, tzinfo=timezone.utc)

        result = compute_dynamic_bitmask(sunrise, sunset, fill_value="1")
        assert result == "000000011111111111110000"

    def test_midnight_crossing(self) -> None:
        """Sunrise at 22:00, sunset at 4:00 (wraps midnight) — fill hours 22-3."""
        sunrise = datetime(2026, 6, 21, 22, 0, tzinfo=timezone.utc)
        sunset = datetime(2026, 6, 22, 4, 0, tzinfo=timezone.utc)

        result = compute_dynamic_bitmask(sunrise, sunset, fill_value="1")
        # Hours 22,23,0,1,2,3 are active
        assert result == "111100000000000000000011"

    def test_all_day_active(self) -> None:
        """Sunrise at 0:00, sunset at 0:00 next day -> all 24 hours active."""
        sunrise = datetime(2026, 6, 21, 0, 0, tzinfo=timezone.utc)
        sunset = datetime(2026, 6, 22, 0, 0, tzinfo=timezone.utc)

        result = compute_dynamic_bitmask(sunrise, sunset, fill_value="1")
        assert result == "1" * 24

    def test_offset_causes_midnight_crossing(self) -> None:
        """Sunrise at 1:00 with -120min offset -> effective at 23:00 previous day."""
        sunrise = datetime(2026, 6, 21, 1, 0, tzinfo=timezone.utc)
        sunset = datetime(2026, 6, 21, 20, 0, tzinfo=timezone.utc)

        result = compute_dynamic_bitmask(
            sunrise, sunset, sunrise_offset_minutes=-120, fill_value="1"
        )
        # Effective sunrise at 23:00, sunset at 20:00
        # This wraps: hours 23,0-19 active, hours 20-22 inactive
        assert result == "111111111111111111110001"
