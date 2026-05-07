from __future__ import annotations

import logging

from aiohttp import web

from banger_link.db.connection import Database

logger = logging.getLogger(__name__)


class HealthServer:
    """Tiny aiohttp /health endpoint used by Docker's healthcheck."""

    def __init__(self, db: Database, port: int) -> None:
        self._db = db
        self._port = port
        self._runner: web.AppRunner | None = None

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/health", self._handler)
        app.router.add_get("/", self._handler)
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=self._port)
        await site.start()
        self._runner = runner
        logger.info("Health server listening on :%d", self._port)

    async def stop(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    async def _handler(self, request: web.Request) -> web.Response:
        ok = await self._db.healthcheck()
        status = 200 if ok else 503
        return web.json_response({"status": "ok" if ok else "fail"}, status=status)
