import os
import types
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch


class TestTopnDbClient(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Ensure required env var exists for modules that rely on it
        os.environ.setdefault("TOPN_DB_BASE_URL", "http://api")
        # Provide a dummy langchain_groq for core.config import safety
        import sys

        sys.modules.setdefault("langchain_groq", types.SimpleNamespace(ChatGroq=object))

        # Import after environment prepared
        from clients.topn_db_client import TopnDbClient

        self.TopnDbClient = TopnDbClient
        self.httpx_client = AsyncMock()
        self.client = TopnDbClient(base_url="http://api", client=self.httpx_client)

    async def asyncTearDown(self):
        pass

    async def test_context_manager_closes_own_client_only(self):
        from clients.topn_db_client import TopnDbClient

        # Own client
        c1 = TopnDbClient(base_url="http://api", client=None)
        async with c1:
            self.assertIsNotNone(c1.client)
        # should close
        # Cannot easily assert closed, but ensure aclose called by spying
        with patch.object(c1.client, "aclose", new=AsyncMock()) as a:
            await c1.__aexit__(None, None, None)
            a.assert_awaited()

        # External client - should not close in __aexit__
        ext = AsyncMock()
        c2 = TopnDbClient(base_url="http://api", client=ext)
        await c2.__aexit__(None, None, None)
        ext.aclose.assert_not_called()

    async def test_make_request_success_json_and_204(self):
        # 200 JSON
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"ok": True}
        resp.raise_for_status.return_value = None
        self.httpx_client.request = AsyncMock(return_value=resp)
        data = await self.client._make_request("GET", "/x")
        self.assertEqual(data, {"ok": True})

        # 204 no content
        resp_204 = MagicMock()
        resp_204.status_code = 204
        resp_204.raise_for_status.return_value = None
        self.httpx_client.request = AsyncMock(return_value=resp_204)
        data2 = await self.client._make_request("DELETE", "/y")
        self.assertEqual(data2, {"success": True})

    async def test_make_request_http_error_and_exception(self):
        import httpx

        err_resp = MagicMock()
        err_resp.status_code = 500
        http_err = httpx.HTTPStatusError("boom", request=MagicMock(), response=err_resp)
        bad = AsyncMock(side_effect=http_err)
        self.httpx_client.request = bad
        with self.assertRaises(httpx.HTTPStatusError):
            await self.client._make_request("GET", "/err")

        generic = AsyncMock(side_effect=RuntimeError("x"))
        self.httpx_client.request = generic
        with self.assertRaises(RuntimeError):
            await self.client._make_request("GET", "/err2")

    async def test_endpoint_helpers_call_make_request_correctly(self):
        c = self.client
        with patch.object(
            c, "_make_request", new=AsyncMock(return_value={"a": 1})
        ) as mr:
            await c.get_api_root()
            mr.assert_awaited_with("GET", "/")
            await c.health_check()
            mr.assert_awaited_with("GET", "/health")
            await c.get_all_tasks()
            mr.assert_awaited_with("GET", "/api/v1/tasks/")
            await c.get_tasks_by_chat_id("1")
            mr.assert_awaited_with("GET", f"/api/v1/tasks/chat/1")
            await c.get_task_by_id(2)
            mr.assert_awaited_with("GET", f"/api/v1/tasks/2")
            await c.create_task({"n": 1})
            mr.assert_awaited_with("POST", "/api/v1/tasks/", json_data={"n": 1})
            await c.update_task(3, {"a": 2})
            mr.assert_awaited_with("PUT", f"/api/v1/tasks/3", json_data={"a": 2})
            await c.delete_task_by_id(4)
            mr.assert_awaited_with("DELETE", f"/api/v1/tasks/4")
            await c.delete_tasks_by_chat_id("7", name=None)
            mr.assert_awaited_with("DELETE", f"/api/v1/tasks/chat/7", params=None)
            await c.delete_tasks_by_chat_id("7", name="foo")
            mr.assert_awaited_with(
                "DELETE", f"/api/v1/tasks/chat/7", params={"name": "foo"}
            )
            await c.get_pending_tasks()
            mr.assert_awaited_with("GET", "/api/v1/tasks/pending")
            await c.update_last_got_item_timestamp(9)
            mr.assert_awaited_with("POST", f"/api/v1/tasks/9/update-last-got-item")
            await c.get_items_to_send_for_task(11)
            mr.assert_awaited_with("GET", f"/api/v1/tasks/11/items-to-send")
            await c.get_all_items(skip=1, limit=2)
            mr.assert_awaited_with(
                "GET", "/api/v1/items/", params={"skip": 1, "limit": 2}
            )
            await c.get_items_by_source_url("u", limit=5)
            mr.assert_awaited_with(
                "GET", "/api/v1/items/by-source", params={"source_url": "u", "limit": 5}
            )
            await c.get_recent_items(hours=3, limit=4)
            mr.assert_awaited_with(
                "GET", "/api/v1/items/recent", params={"hours": 3, "limit": 4}
            )
            await c.get_item_by_id(13)
            mr.assert_awaited_with("GET", f"/api/v1/items/13")
            await c.get_item_by_url("http://u")
            mr.assert_awaited_with("GET", f"/api/v1/items/by-url/http://u")
            await c.create_item({"x": 1})
            mr.assert_awaited_with("POST", "/api/v1/items/", json_data={"x": 1})
            await c.delete_item_by_id(15)
            mr.assert_awaited_with("DELETE", f"/api/v1/items/15")
