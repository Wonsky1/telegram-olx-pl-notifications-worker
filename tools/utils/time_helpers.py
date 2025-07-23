"""Utility helpers related to time handling.

Currently contains TimeUtils.within_last_minutes which is a refactor of
`is_time_within_last_n_minutes` from the old tools.utils module.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pytz

from core.config import settings

logger = logging.getLogger(__name__)


class TimeUtils:
    """Collection of static helpers for dealing with OLX time strings."""

    @staticmethod
    def within_last_minutes(time_str: str, n: int | None = None) -> bool:
        """Return True if the given HH:MM string is within *n* minutes from now.

        OLX uses UTC time for the `Dzisiaj o HH:MM` indicator. This helper
        converts the given time to a timezone-aware datetime in UTC and checks
        if it is not older than *n* minutes.

        Args:
            time_str: A time formatted as 'HH:MM'.
            n: Number of minutes. Defaults to settings.DEFAULT_LAST_MINUTES_GETTING.
        """
        if n is None:
            n = settings.DEFAULT_LAST_MINUTES_GETTING

        time_format = "%H:%M"
        try:
            parsed_time = datetime.strptime(time_str, time_format).time()
            utc_tz = pytz.UTC
            now_utc = datetime.now(utc_tz)
            time_provided_utc = utc_tz.localize(
                datetime.combine(now_utc.date(), parsed_time)
            )
            n_minutes_ago_utc = now_utc - timedelta(minutes=n)
            return time_provided_utc >= n_minutes_ago_utc
        except ValueError:
            logger.error("Invalid time format received from OLX: %s", time_str)
            return False
