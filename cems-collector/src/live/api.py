"""Opt-in loopback simulation pilot. Never imports the DB-backed API."""
from __future__ import annotations

import asyncio
import threading
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.config import CemsConfig
from src.live.cache import MAX_HISTORY_POINTS, RollingCache
from src.live.collector import LiveCollector, SimulatedSource, SingleOwner
from src.services.registry import load_registry


def create_app(*, cache=None, collector=None, start_collector=True):
    if cache is None:
        registry = load_registry(CemsConfig(parameter_registry_path=str(
            Path(__file__).resolve().parents[2] / 'registry' / 'cems-parameters.yaml')))
        specs = [p for p in registry.parameters if p.stack_id == '1' and p.collect_enabled]
        stack = next(s for s in registry.stacks if s.stack_id == '1')
        cache = RollingCache(specs, source_mode='simulation')
        collector = LiveCollector(cache, SimulatedSource(), stack)
    if start_collector and collector is None:
        raise ValueError('collector required')

    @asynccontextmanager
    async def lifespan(app):
        stop, worker = threading.Event(), None
        owner = SingleOwner(collector.source.identity) if start_collector else None
        async def expire_idle():
            while True:
                await asyncio.sleep(1)
                cache.expire()

        sweeper = None
        try:
            if owner:
                # Fail before serving if another pilot owns this source.
                owner.__enter__()
                worker = threading.Thread(target=collector.run, args=(stop,),
                                          kwargs={'acquire_owner': False}, daemon=True)
                worker.start()
            sweeper = asyncio.create_task(expire_idle())
            yield
        finally:
            stop.set()
            if sweeper:
                sweeper.cancel()
                with suppress(asyncio.CancelledError):
                    await sweeper
            if worker:
                worker.join(timeout=5.0)
            cache.clear()
            if owner:
                owner.__exit__()

    app = FastAPI(title='CEMS volatile pilot', lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', '[::1]', 'testserver'])
    app.state.cache = cache
    pending = 0

    @app.middleware('http')
    async def bounded_read_only(request, call_next):
        nonlocal pending
        from starlette.responses import JSONResponse
        if request.method not in {'GET', 'HEAD'}:
            response = JSONResponse({'detail': 'read-only API'}, status_code=405)
        elif pending >= 16:
            response = JSONResponse({'detail': 'busy; retry later'}, status_code=503)
        else:
            pending += 1
            try:
                response = await call_next(request)
            finally:
                pending -= 1
        response.headers['Cache-Control'] = 'no-store, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.get('/v1/cems/snapshot')
    def snapshot():
        return cache.snapshot()

    @app.get('/v1/cems/history')
    def history(parameter: str = Query(..., min_length=1, max_length=64),
                limit: int = Query(360, ge=1, le=MAX_HISTORY_POINTS)):
        try:
            return cache.history(parameter, limit)
        except KeyError:
            raise HTTPException(status_code=404, detail='unknown parameter') from None

    @app.get('/v1/cems/signals')
    def signals():
        return cache.signals()

    @app.get('/health')
    def health():
        state = cache.snapshot()
        return {'status': state['status'], 'source_mode': cache.source_mode,
                'storage': 'process_memory', 'poll_interval_seconds': 5,
                'retention_seconds': 21600}

    return app
