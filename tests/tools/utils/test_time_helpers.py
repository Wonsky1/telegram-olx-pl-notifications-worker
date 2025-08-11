from unittest import IsolatedAsyncioTestCase

from tools.utils.time_helpers import TimeUtils


class TestTimeUtils(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        pass

    async def asyncTearDown(self):
        pass

    async def test_within_last_minutes_true_false(self):
        # Assuming now is >= 00:10
        self.assertTrue(TimeUtils.within_last_minutes("23:59", n=24 * 60))
        self.assertFalse(TimeUtils.within_last_minutes("00:00", n=0))

    async def test_invalid_format_returns_false(self):
        self.assertFalse(TimeUtils.within_last_minutes("bad", n=10))
