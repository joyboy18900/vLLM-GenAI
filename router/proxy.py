"""State of the pods and the proxy logic of the router. The HTTP layer is in main.py."""
import asyncio
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import httpx
from prometheus_client import CollectorRegistry, Counter, Histogram

from scoring import PodState, Weights, choose_pod, parse_vllm_metrics, score

log = logging.getLogger("router")

MAX_PREFIXES = 256       # prefix keys that the router remembers for each pod
METRICS_TIMEOUT = 2.0    # seconds for one /metrics request of a pod


@dataclass(frozen=True)
class PodInfo:
    name: str
    url: str


class NoReadyPod(Exception):
    """No pod can take the request (none is ready, or the retry failed too)."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


@dataclass
class ChatResult:
    status: int
    content_type: str
    pod: str
    body: object  # bytes, or an async iterator of bytes for a stream


class _Pod:
    def __init__(self, info):
        self.info = info
        self.ready = False
        self.waiting = 0.0
        self.running = 0.0
        self.kv_usage = 0.0
        self.in_flight = 0
        self.last_active = 0.0
        self.prefixes = OrderedDict()

    def state(self):
        return PodState(name=self.info.name, ready=self.ready, waiting=self.waiting,
                        running=self.running, in_flight=self.in_flight, kv_usage=self.kv_usage,
                        prefixes=frozenset(self.prefixes))

    def remember(self, key):
        self.prefixes[key] = True
        self.prefixes.move_to_end(key)
        while len(self.prefixes) > MAX_PREFIXES:
            self.prefixes.popitem(last=False)


class StaticPodSource:
    """Pod list from a string like "a=http://host-a:8000,b=http://host-b:8000"."""

    def __init__(self, spec):
        self._pods = []
        for item in filter(None, (x.strip() for x in spec.split(","))):
            name, _, url = item.partition("=")
            if not url:
                raise ValueError(f"bad pod entry: {item!r}")
            self._pods.append(PodInfo(name=name, url=url.rstrip("/")))

    async def __call__(self):
        return list(self._pods)


class RouterCore:
    def __init__(self, source, client, weights: Weights, scaler=None, hold_seconds=120.0,
                 clock=time.monotonic, sleep=asyncio.sleep):
        self._source = source
        self._client = client
        self._weights = weights
        self._scaler = scaler
        self._hold_seconds = hold_seconds
        self._clock = clock
        self._sleep = sleep
        self._wake_lock = asyncio.Lock()
        self._pods = {}
        self.upstream_errors = 0
        self.registry = CollectorRegistry()
        self._requests = Counter("router_requests_total", "Requests sent to a pod, by the status of the answer.",
                                 ["pod", "status"], registry=self.registry)
        self._errors = Counter("router_upstream_errors_total", "Failed requests to a pod.",
                               registry=self.registry)
        self._scale_events = Counter("router_scale_events_total", "Scale changes made by the router.",
                                     ["direction"], registry=self.registry)
        self._cold_wait = Histogram("router_cold_start_wait_seconds",
                                    "Time that a request waited for a pod to start.",
                                    buckets=(1, 5, 10, 20, 30, 45, 60, 90, 120), registry=self.registry)
        if scaler is not None:
            scaler.on_event = lambda d: self._scale_events.labels(d).inc()

    # state

    def states(self):
        return [p.state() for _, p in sorted(self._pods.items())]

    def stats(self):
        rows = []
        for _, p in sorted(self._pods.items()):
            st = p.state()
            rows.append({"name": st.name, "url": p.info.url, "ready": st.ready, "waiting": st.waiting,
                         "running": st.running, "in_flight": st.in_flight, "kv_usage": st.kv_usage,
                         "prefixes": len(st.prefixes), "score": score(st, "", self._weights)})
        return rows

    async def refresh(self):
        infos = await self._source()
        names = {i.name for i in infos}
        for gone in set(self._pods) - names:
            del self._pods[gone]
        for info in infos:
            if info.name not in self._pods or self._pods[info.name].info != info:
                old = self._pods.get(info.name)
                new = _Pod(info)
                new.last_active = self._clock()
                if old:
                    new.in_flight = old.in_flight
                    new.last_active = old.last_active
                self._pods[info.name] = new
        await asyncio.gather(*(self._poll(p) for p in self._pods.values()))

    async def _poll(self, pod):
        try:
            r = await self._client.get(f"{pod.info.url}/metrics", timeout=METRICS_TIMEOUT)
            r.raise_for_status()
            m = parse_vllm_metrics(r.text)
        except (httpx.HTTPError, ValueError) as exc:
            if pod.ready:
                log.warning("pod %s left the pool: %s", pod.info.name, exc)
            pod.ready = False
            return
        pod.ready, pod.waiting, pod.running, pod.kv_usage = True, m.waiting, m.running, m.kv_usage

    async def run_poll(self, interval):
        while True:
            try:
                await self.refresh()
                await self.autoscale_tick()
            except Exception:  # keep the loop alive
                log.exception("refresh failed")
            await asyncio.sleep(interval)

    # proxy

    def ready_pod_for_models(self):
        ready = [p for _, p in sorted(self._pods.items()) if p.ready]
        return ready[0] if ready else None

    async def models(self):
        pod = self.ready_pod_for_models()
        if pod is None:
            raise NoReadyPod("No ready pod")
        r = await self._client.get(f"{pod.info.url}/v1/models", timeout=METRICS_TIMEOUT)
        return ChatResult(r.status_code, r.headers.get("content-type", "application/json"), pod.info.name, r.content)

    async def chat(self, body, key) -> ChatResult:
        stream = bool(body.get("stream"))
        raw = json.dumps(body).encode()
        tried = set()
        if self._scaler is not None and not any(s.ready for s in self.states()):
            await self._wait_for_a_pod()
        for _attempt in range(2):  # the first try and one retry
            states = [s for s in self.states() if s.name not in tried]
            choice = choose_pod(states, key, self._weights)
            if choice is None:
                break
            pod = self._pods[choice.name]
            tried.add(pod.info.name)
            pod.in_flight += 1
            pod.last_active = self._clock()
            try:
                result = await self._send(pod, raw, stream, key)
            except httpx.HTTPError as exc:
                self._fail(pod, exc)
                continue
            if result is None:  # a 5xx answer before any body
                self._fail(pod, "5xx answer")
                continue
            return result
        raise NoReadyPod("All pods failed" if tried else "No ready pod")

    async def _wait_for_a_pod(self):
        """Scale a pod up and hold the request until a pod is ready (cold start), or fail after hold_seconds."""
        start = self._clock()
        async with self._wake_lock:  # a second request does not scale again
            await self.refresh()
            if not any(s.ready for s in self.states()):
                await self._scaler.wake()
        while True:
            await self.refresh()
            if any(s.ready for s in self.states()):
                self._cold_wait.observe(self._clock() - start)
                return
            if self._clock() - start >= self._hold_seconds:
                raise NoReadyPod(f"No pod became ready in {self._hold_seconds:.0f} seconds")
            await self._sleep(1.0)

    async def autoscale_tick(self):
        """Scale idle pods to zero (the always-on pod stays)."""
        if self._scaler is None:
            return
        now = self._clock()
        await self._scaler.scale_down_idle(
            [(n, now - p.last_active, p.in_flight) for n, p in sorted(self._pods.items()) if p.ready])

    def _release(self, pod):
        pod.in_flight -= 1
        pod.last_active = self._clock()

    def _fail(self, pod, why):
        self._release(pod)
        pod.ready = False
        self.upstream_errors += 1
        self._errors.inc()
        log.warning("pod %s failed: %s", pod.info.name, why)

    async def _send(self, pod, raw, stream, key) -> Optional[ChatResult]:
        url = f"{pod.info.url}/v1/chat/completions"
        headers = {"content-type": "application/json"}
        if not stream:
            r = await self._client.post(url, content=raw, headers=headers)
            if r.status_code >= 500:
                return None
            self._release(pod)
            pod.remember(key)
            self._requests.labels(pod.info.name, str(r.status_code)).inc()
            return ChatResult(r.status_code, r.headers.get("content-type", "application/json"),
                              pod.info.name, r.content)
        req = self._client.build_request("POST", url, content=raw, headers=headers)
        r = await self._client.send(req, stream=True)
        if r.status_code >= 500:
            await r.aclose()
            return None
        pod.remember(key)
        self._requests.labels(pod.info.name, str(r.status_code)).inc()
        return ChatResult(r.status_code, r.headers.get("content-type", "text/event-stream"),
                          pod.info.name, self._relay(pod, r))

    async def _relay(self, pod, response) -> AsyncIterator[bytes]:
        try:
            async for chunk in response.aiter_raw():
                yield chunk
        except Exception:
            self.upstream_errors += 1
            self._errors.inc()
            log.warning("stream of pod %s broke", pod.info.name)
            raise
        finally:
            self._release(pod)
            await response.aclose()
