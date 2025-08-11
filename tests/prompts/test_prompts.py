from unittest import IsolatedAsyncioTestCase

from prompts import get_description_summary_prompt


class TestPrompts(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        pass

    async def asyncTearDown(self):
        pass

    async def test_get_description_summary_prompt_contains_description_and_format(self):
        p = get_description_summary_prompt("hello")
        self.assertIn("hello", p)
        for line in ["price:", "deposit:", "animals_allowed:", "rent:"]:
            self.assertIn(line, p)
