import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
import pytest
from fastapi.testclient import TestClient

from main import create_app
from proxy import PodInfo, RouterCore
from scoring import Weights

W = Weights(prefix_bonus=3.0, queue=1.0, kv=2.0)


def metrics_text(waiting=0, running=0, kv=0.0):
    return (f"vllm:num_requests_waiting{{engine=\"0\"}} {waiting}\n"
            f"vllm:num_requests_running{{engine=\"0\"}} {running}\n"
            f"vllm:kv_cache_usage_perc{{engine=\"0\"}} {kv}\n")


class FakePod:
    """Behavior of one fake vLLM pod. `calls` counts requests to /v1/chat/completions."""

    def __init__(self, waiting=0, metrics_ok=True, chat_status=200, chat_error=None,
                 stream_chunks=None, break_stream=False):
        self.waiting = waiting
        self.metrics_ok = metrics_ok
        self.chat_status = chat_status
        self.chat_error = chat_error
        self.stream_chunks = stream_chunks or [b'data: {"x":1}\n\n', b"data: [DONE]\n\n"]
        self.break_stream = break_stream
        self.calls = 0
        self.last_body = None


class MidStreamError(Exception):
    pass


class FakeStream(httpx.AsyncByteStream):
    def __init__(self, chunks, break_after):
        self.chunks = chunks
        self.break_after = break_after

    async def __aiter__(self):
        for i, c in enumerate(self.chunks):
            if self.break_after is not None and i == self.break_after:
                raise MidStreamError("pod died")
            yield c


def make_transport(pods):
    def handler(request: httpx.Request) -> httpx.Response:
        pod = pods[request.url.host]
        path = request.url.path
        if path == "/metrics":
            if not pod.metrics_ok:
                raise httpx.ConnectError("down")
            return httpx.Response(200, text=metrics_text(waiting=pod.waiting))
        if path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "Qwen/Qwen2.5-3B-Instruct"}]})
        if path == "/v1/chat/completions":
            pod.calls += 1
            pod.last_body = json.loads(request.content)
            if pod.chat_error:
                raise pod.chat_error
            if pod.chat_status != 200:
                return httpx.Response(pod.chat_status, json={"error": "x"})
            if pod.last_body.get("stream"):
                return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                      stream=FakeStream(pod.stream_chunks, 1 if pod.break_stream else None))
            return httpx.Response(200, json={"choices": [{"message": {"content": "hi from " + request.url.host}}]})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def build(pods, **kw):
    infos = [PodInfo(name=n, url=f"http://{n}:8000") for n in pods]
    client = httpx.AsyncClient(transport=make_transport(pods))

    async def source():
        return infos

    core = RouterCore(source, client, W, **kw)
    asyncio.run(core.refresh())
    return core


def body(content="hello", stream=False, system="S"):
    return {"model": "m", "stream": stream,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}]}


def post(client, **kw):
    return client.post("/v1/chat/completions", json=body(**kw))


# refresh

def test_refresh_reads_the_metrics_of_each_pod():
    pods = {"a": FakePod(waiting=4), "b": FakePod()}
    core = build(pods)
    state = {s.name: s for s in core.states()}
    assert state["a"].ready and state["a"].waiting == 4
    assert state["b"].ready and state["b"].waiting == 0


def test_a_pod_without_metrics_is_not_ready_until_it_answers_again():
    pods = {"a": FakePod(metrics_ok=False), "b": FakePod()}
    core = build(pods)
    assert [s.name for s in core.states() if s.ready] == ["b"]
    pods["a"].metrics_ok = True
    asyncio.run(core.refresh())
    assert [s.name for s in core.states() if s.ready] == ["a", "b"]


# non-stream

def test_chat_answer_and_routed_pod_header():
    core = build({"a": FakePod()})
    r = post(TestClient(create_app(core)))
    assert r.status_code == 200
    assert r.headers["x-routed-pod"] == "a"
    assert r.json()["choices"][0]["message"]["content"] == "hi from a"


def test_the_pod_with_the_shorter_queue_gets_the_request():
    core = build({"a": FakePod(waiting=5), "b": FakePod(waiting=0)})
    r = post(TestClient(create_app(core)))
    assert r.headers["x-routed-pod"] == "b"


def test_a_known_prefix_goes_to_the_same_pod():
    pods = {"a": FakePod(), "b": FakePod()}
    core = build(pods)
    c = TestClient(create_app(core))
    first = post(c, content="same start").headers["x-routed-pod"]
    other = "b" if first == "a" else "a"
    pods[first].waiting = 1  # a small queue is below the prefix bonus
    asyncio.run(core.refresh())
    assert post(c, content="same start").headers["x-routed-pod"] == first
    assert pods[other].calls == 0


def test_in_flight_is_zero_after_the_request():
    core = build({"a": FakePod()})
    post(TestClient(create_app(core)))
    assert [s.in_flight for s in core.states()] == [0]


def test_invalid_json_is_a_400():
    core = build({"a": FakePod()})
    r = TestClient(create_app(core)).post("/v1/chat/completions", content=b"{bad",
                                          headers={"content-type": "application/json"})
    assert r.status_code == 400


# stream

def test_stream_passes_the_chunks_in_order():
    core = build({"a": FakePod(stream_chunks=[b"data: 1\n\n", b"data: 2\n\n", b"data: [DONE]\n\n"])})
    with TestClient(create_app(core)).stream("POST", "/v1/chat/completions", json=body(stream=True)) as r:
        assert r.headers["x-routed-pod"] == "a"
        assert r.headers["content-type"].startswith("text/event-stream")
        data = b"".join(r.iter_bytes())
    assert data == b"data: 1\n\ndata: 2\n\ndata: [DONE]\n\n"


def test_stream_in_flight_is_zero_after_the_stream():
    core = build({"a": FakePod()})
    with TestClient(create_app(core)).stream("POST", "/v1/chat/completions", json=body(stream=True)) as r:
        list(r.iter_bytes())
    assert [s.in_flight for s in core.states()] == [0]


# errors and retry

def test_retry_on_another_pod_when_the_chosen_pod_cannot_connect():
    pods = {"a": FakePod(chat_error=httpx.ConnectError("refused")), "b": FakePod(waiting=3)}
    core = build(pods)  # "a" has the better score, so it is chosen first
    r = post(TestClient(create_app(core)))
    assert r.status_code == 200
    assert r.headers["x-routed-pod"] == "b"
    assert pods["a"].calls == 1 and pods["b"].calls == 1


def test_retry_on_a_5xx_before_the_stream_starts():
    pods = {"a": FakePod(chat_status=503), "b": FakePod(waiting=3)}
    core = build(pods)
    with TestClient(create_app(core)).stream("POST", "/v1/chat/completions", json=body(stream=True)) as r:
        assert r.status_code == 200
        assert r.headers["x-routed-pod"] == "b"
        list(r.iter_bytes())


def test_a_4xx_answer_is_passed_on_with_no_retry():
    pods = {"a": FakePod(chat_status=400), "b": FakePod(waiting=3)}
    core = build(pods)
    r = post(TestClient(create_app(core)))
    assert r.status_code == 400
    assert pods["b"].calls == 0


def test_only_one_retry():
    pods = {n: FakePod(chat_error=httpx.ConnectError("x"), waiting=i) for i, n in enumerate("abc")}
    core = build(pods)
    r = post(TestClient(create_app(core)))
    assert r.status_code == 503
    assert pods["a"].calls == 1 and pods["b"].calls == 1 and pods["c"].calls == 0


def test_no_retry_after_the_stream_started():
    pods = {"a": FakePod(break_stream=True), "b": FakePod(waiting=3)}
    core = build(pods)

    async def run():
        resp = await core.chat(body(stream=True), "k")
        got = []
        with pytest.raises(MidStreamError):
            async for chunk in resp.body:
                got.append(chunk)
        return resp, got

    resp, got = asyncio.run(run())
    assert resp.pod == "a" and got == [b'data: {"x":1}\n\n']
    assert pods["b"].calls == 0
    assert [s.in_flight for s in core.states()] == [0, 0]
    assert core.upstream_errors == 1


def test_a_failed_pod_leaves_the_pool_until_the_next_refresh():
    pods = {"a": FakePod(chat_error=httpx.ConnectError("x")), "b": FakePod(waiting=3)}
    core = build(pods)
    post(TestClient(create_app(core)))
    assert [s.ready for s in core.states() if s.name == "a"] == [False]
    pods["a"].chat_error = None
    asyncio.run(core.refresh())
    assert [s.ready for s in core.states() if s.name == "a"] == [True]


def test_503_when_no_pod_is_ready():
    core = build({"a": FakePod(metrics_ok=False)})
    r = post(TestClient(create_app(core)))
    assert r.status_code == 503
    assert "no ready pod" in r.json()["error"]["message"].lower()


def test_error_count_and_request_metrics():
    pods = {"a": FakePod(chat_error=httpx.ConnectError("x")), "b": FakePod(waiting=3)}
    core = build(pods)
    c = TestClient(create_app(core))
    post(c)
    text = c.get("/metrics").text
    assert 'router_requests_total{pod="b",status="200"} 1.0' in text
    assert "router_upstream_errors_total" in text and core.upstream_errors == 1


# other endpoints

def test_models_goes_to_a_ready_pod():
    core = build({"a": FakePod()})
    r = TestClient(create_app(core)).get("/v1/models")
    assert r.status_code == 200 and r.json()["data"][0]["id"] == "Qwen/Qwen2.5-3B-Instruct"


def test_models_is_503_when_no_pod_is_ready():
    core = build({"a": FakePod(metrics_ok=False)})
    assert TestClient(create_app(core)).get("/v1/models").status_code == 503


def test_health_is_ok_and_counts_ready_pods():
    core = build({"a": FakePod(), "b": FakePod(metrics_ok=False)})
    r = TestClient(create_app(core)).get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok", "ready_pods": 1, "pods": 2}


def test_router_stats_shows_the_state_and_score_of_each_pod():
    core = build({"a": FakePod(waiting=2), "b": FakePod()})
    data = TestClient(create_app(core)).get("/router/stats").json()
    by = {p["name"]: p for p in data["pods"]}
    assert by["a"]["ready"] is True and by["a"]["waiting"] == 2
    assert by["a"]["score"] == -2.0 and by["b"]["score"] == 0.0
    assert set(by["a"]) >= {"name", "url", "ready", "waiting", "running", "in_flight", "kv_usage", "prefixes", "score"}


# scale to zero, hold, and idle scale-down

from scaling import Scaler  # noqa: E402


class FakeClock:
    def __init__(self):
        self.t = 0.0
        self.sleeps = 0
        self.on_sleep = None  # called after each sleep, for a fake pod that starts

    def now(self):
        return self.t

    async def sleep(self, s):
        self.t += s
        self.sleeps += 1
        if self.on_sleep:
            self.on_sleep(self.t)


class FakeScale:
    def __init__(self, replicas, on_set=None):
        self.replicas = dict(replicas)
        self.sets = []
        self.on_set = on_set

    async def get_replicas(self, d):
        return self.replicas[d]

    async def set_replicas(self, d, n):
        self.sets.append((d, n))
        self.replicas[d] = n
        if self.on_set:
            self.on_set(d, n)


def build_scaled(pods, replicas, clock, on_set=None, idle=600, hold=120):
    infos = [PodInfo(name=n, url=f"http://{n}:8000") for n in pods]
    client = httpx.AsyncClient(transport=make_transport(pods))

    async def source():
        return infos

    scale = FakeScale(replicas, on_set)
    scaler = Scaler(scale, {"a": "vllm-awq-a", "b": "vllm-awq-b"}, always_on={"a"}, idle_seconds=idle)
    core = RouterCore(source, client, W, scaler=scaler, hold_seconds=hold, clock=clock.now, sleep=clock.sleep)
    asyncio.run(core.refresh())
    return core, scale


def test_a_request_with_no_ready_pod_wakes_a_pod_and_waits_for_it():
    pods = {"b": FakePod(metrics_ok=False)}
    clock = FakeClock()
    core, scale = build_scaled(pods, {"vllm-awq-a": 1, "vllm-awq-b": 0}, clock,
                               on_set=lambda d, n: setattr(clock, "on_sleep",
                                                           lambda t: setattr(pods["b"], "metrics_ok", t >= 30)))
    r = post(TestClient(create_app(core)))
    assert r.status_code == 200 and r.headers["x-routed-pod"] == "b"
    assert scale.sets == [("vllm-awq-b", 1)]
    assert clock.t >= 30


def test_the_hold_ends_with_a_503_after_the_limit():
    pods = {"b": FakePod(metrics_ok=False)}
    clock = FakeClock()
    core, scale = build_scaled(pods, {"vllm-awq-a": 1, "vllm-awq-b": 0}, clock, hold=120)
    r = post(TestClient(create_app(core)))
    assert r.status_code == 503
    assert "120" in r.json()["error"]["message"]
    assert 120 <= clock.t < 130


def test_two_requests_in_the_hold_wake_the_pod_once():
    pods = {"b": FakePod(metrics_ok=False)}
    clock = FakeClock()
    core, scale = build_scaled(pods, {"vllm-awq-a": 1, "vllm-awq-b": 0}, clock,
                               on_set=lambda d, n: setattr(clock, "on_sleep",
                                                           lambda t: setattr(pods["b"], "metrics_ok", t >= 10)))

    async def two():
        r1, r2 = await asyncio.gather(core.chat(body(), "k1"), core.chat(body(), "k2"))
        return r1, r2

    r1, r2 = asyncio.run(two())
    assert r1.pod == "b" and r2.pod == "b"
    assert scale.sets == [("vllm-awq-b", 1)]


def test_the_wait_is_counted_in_the_metrics():
    pods = {"b": FakePod(metrics_ok=False)}
    clock = FakeClock()
    core, _ = build_scaled(pods, {"vllm-awq-a": 1, "vllm-awq-b": 0}, clock,
                           on_set=lambda d, n: setattr(clock, "on_sleep",
                                                       lambda t: setattr(pods["b"], "metrics_ok", t >= 5)))
    c = TestClient(create_app(core))
    post(c)
    text = c.get("/metrics").text
    assert 'router_scale_events_total{direction="up"} 1.0' in text
    assert "router_cold_start_wait_seconds_count 1.0" in text


def test_no_wake_when_a_pod_is_ready():
    pods = {"a": FakePod(), "b": FakePod(metrics_ok=False)}
    clock = FakeClock()
    core, scale = build_scaled(pods, {"vllm-awq-a": 1, "vllm-awq-b": 0}, clock)
    assert post(TestClient(create_app(core))).status_code == 200
    assert scale.sets == []


def test_an_idle_pod_is_scaled_down_by_the_tick_and_the_always_on_pod_stays():
    pods = {"a": FakePod(), "b": FakePod()}
    clock = FakeClock()
    core, scale = build_scaled(pods, {"vllm-awq-a": 1, "vllm-awq-b": 1}, clock, idle=600)
    clock.t = 601
    asyncio.run(core.autoscale_tick())
    assert scale.sets == [("vllm-awq-b", 0)]


def test_a_recent_request_keeps_the_pod():
    pods = {"a": FakePod(), "b": FakePod()}
    clock = FakeClock()
    core, scale = build_scaled(pods, {"vllm-awq-a": 1, "vllm-awq-b": 1}, clock, idle=600)
    clock.t = 500
    c = TestClient(create_app(core))
    for _ in range(3):  # fill pod "a", so that "b" gets one request too
        post(c, content=str(_))
    pods["a"].waiting = 9
    asyncio.run(core.refresh())
    r = post(c, content="to b")
    assert r.headers["x-routed-pod"] == "b"
    clock.t = 1000  # 500 s after the last request of "b"
    asyncio.run(core.autoscale_tick())
    assert scale.sets == []
    clock.t = 1101  # more than 600 s
    asyncio.run(core.autoscale_tick())
    assert scale.sets == [("vllm-awq-b", 0)]


# gauges for Prometheus

def test_pod_up_and_score_gauges_follow_the_pods():
    core = build({"a": FakePod(waiting=2), "b": FakePod(metrics_ok=False)})
    text = TestClient(create_app(core)).get("/metrics").text
    assert 'router_pod_up{pod="a"} 1.0' in text
    assert 'router_pod_up{pod="b"} 0.0' in text
    assert 'router_route_score{pod="a"} -2.0' in text


def test_the_series_of_a_pod_that_left_the_list_is_removed():
    pods = {"a": FakePod(), "b": FakePod()}
    infos = [PodInfo(name=n, url=f"http://{n}:8000") for n in pods]
    client = httpx.AsyncClient(transport=make_transport(pods))

    async def source():
        return list(infos)

    core = RouterCore(source, client, W)
    asyncio.run(core.refresh())
    infos.pop()  # pod "b" is gone (scaled to zero)
    asyncio.run(core.refresh())
    text = TestClient(create_app(core)).get("/metrics").text
    assert 'router_pod_up{pod="a"}' in text
    assert 'router_pod_up{pod="b"}' not in text and 'router_route_score{pod="b"}' not in text
