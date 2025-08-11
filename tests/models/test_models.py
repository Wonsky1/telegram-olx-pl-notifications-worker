from unittest import IsolatedAsyncioTestCase

from models import Item


class TestModels(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        pass

    async def asyncTearDown(self):
        pass

    async def test_item_init_sets_fields(self):
        it = Item(
            title="t",
            price="p",
            image_url="i",
            created_at=None,
            location="l",
            item_url="u",
            description="d",
            created_at_pretty="cp",
        )
        self.assertEqual(it.title, "t")
        self.assertEqual(it.item_url, "u")
