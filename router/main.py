"""HTTP layer of the router: an OpenAI-compatible proxy in front of the vLLM pods."""
import asyncio
import contextlib
import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from k8s_client import in_cluster_source
from proxy import NoReadyPod, RouterCore, StaticPodSource
from scoring import PREFIX_CHARS, prefix_key, weights_from_env


def _error(status, message):
    return JSONResponse({"error": {"message": message, "type": "router_error"}}, status_code=status)


def create_app(core, poll_seconds=0.0):
    @contextlib.asynccontextmanager
    async def lifespan(_app):
        task = asyncio.create_task(core.run_poll(poll_seconds)) if poll_seconds > 0 else None
        try:
            yield
        finally:
            if task:
                task.cancel()

    app = FastAPI(title="LLM-D router", lifespan=lifespan)

    @app.post("/v1/chat/completions")
    async def chat(request: Request):
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("body is not an object")
        except ValueError:
            return _error(400, "The request body is not valid JSON")
        key = prefix_key(body.get("messages") or [], PREFIX_CHARS)
        try:
            result = await core.chat(body, key)
        except NoReadyPod as exc:
            return _error(503, exc.message)
        headers = {"X-Routed-Pod": result.pod}
        if isinstance(result.body, bytes):
            return Response(result.body, status_code=result.status, media_type=result.content_type, headers=headers)
        return StreamingResponse(result.body, status_code=result.status, media_type=result.content_type,
                                 headers=headers)

    @app.get("/v1/models")
    async def models():
        try:
            result = await core.models()
        except NoReadyPod as exc:
            return _error(503, exc.message)
        return Response(result.body, status_code=result.status, media_type=result.content_type,
                        headers={"X-Routed-Pod": result.pod})

    @app.get("/health")
    async def health():
        states = core.states()
        return {"status": "ok", "ready_pods": sum(s.ready for s in states), "pods": len(states)}

    @app.get("/router/stats")
    async def stats():
        return {"pods": core.stats()}

    @app.get("/metrics")
    async def metrics():
        return Response(generate_latest(core.registry), media_type=CONTENT_TYPE_LATEST)

    return app


def app_from_env():
    """Entry point for uvicorn: `uvicorn --factory main:app_from_env`."""
    timeout = float(os.environ.get("ROUTER_UPSTREAM_TIMEOUT", "300"))
    client = httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=5.0))
    if os.environ.get("ROUTER_PODS"):  # a fixed list, for a test outside the cluster
        source = StaticPodSource(os.environ["ROUTER_PODS"])
    else:
        source = in_cluster_source(os.environ.get("ROUTER_POD_SELECTOR", "pool=awq"),
                                   os.environ.get("ROUTER_NAMESPACE"))
    core = RouterCore(source, client, weights_from_env(os.environ))
    return create_app(core, poll_seconds=float(os.environ.get("ROUTER_POLL_SECONDS", "1.5")))
