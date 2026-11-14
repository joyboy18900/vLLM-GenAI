import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scaling import Scaler


class FakeScaleClient:
    def __init__(self, replicas):
        self.replicas = dict(replicas)
        self.sets = []

    async def get_replicas(self, deployment):
        return self.replicas[deployment]

    async def set_replicas(self, deployment, n):
        self.sets.append((deployment, n))
        self.replicas[deployment] = n


MEMBERS = {"a": "vllm-awq-a", "b": "vllm-awq-b"}


def scaler(replicas, events=None, idle=600, always_on=("a",)):
    client = FakeScaleClient(replicas)
    sc = Scaler(client, MEMBERS, always_on=set(always_on), idle_seconds=idle,
                on_event=(events.append if events is not None else None))
    return sc, client


def run(coro):
    return asyncio.run(coro)


# wake

def test_wake_scales_the_first_member_that_is_at_zero():
    sc, client = scaler({"vllm-awq-a": 1, "vllm-awq-b": 0})
    assert run(sc.wake()) == "b"
    assert client.sets == [("vllm-awq-b", 1)]


def test_wake_prefers_the_first_name_in_sort_order():
    sc, client = scaler({"vllm-awq-a": 0, "vllm-awq-b": 0})
    assert run(sc.wake()) == "a"
    assert client.sets == [("vllm-awq-a", 1)]


def test_wake_does_nothing_when_every_member_has_a_replica():
    sc, client = scaler({"vllm-awq-a": 1, "vllm-awq-b": 1})
    assert run(sc.wake()) is None
    assert client.sets == []


def test_wake_reports_an_up_event():
    events = []
    sc, _ = scaler({"vllm-awq-a": 1, "vllm-awq-b": 0}, events)
    run(sc.wake())
    assert events == ["up"]


# scale down

def test_an_idle_member_that_is_not_always_on_goes_to_zero():
    events = []
    sc, client = scaler({"vllm-awq-a": 1, "vllm-awq-b": 1}, events)
    run(sc.scale_down_idle([("b", 601.0, 0)]))
    assert client.sets == [("vllm-awq-b", 0)]
    assert events == ["down"]


def test_the_always_on_member_never_goes_to_zero():
    sc, client = scaler({"vllm-awq-a": 1, "vllm-awq-b": 1})
    run(sc.scale_down_idle([("a", 99999.0, 0)]))
    assert client.sets == []


def test_a_member_below_the_idle_time_stays():
    sc, client = scaler({"vllm-awq-a": 1, "vllm-awq-b": 1}, idle=600)
    run(sc.scale_down_idle([("b", 599.0, 0)]))
    assert client.sets == []


def test_a_member_with_a_request_in_flight_stays():
    sc, client = scaler({"vllm-awq-a": 1, "vllm-awq-b": 1})
    run(sc.scale_down_idle([("b", 9999.0, 1)]))
    assert client.sets == []


def test_a_member_that_is_already_at_zero_gets_no_second_call():
    events = []
    sc, client = scaler({"vllm-awq-a": 1, "vllm-awq-b": 0}, events)
    run(sc.scale_down_idle([("b", 9999.0, 0)]))
    assert client.sets == [] and events == []


def test_an_unknown_member_is_ignored():
    sc, client = scaler({"vllm-awq-a": 1, "vllm-awq-b": 1})
    run(sc.scale_down_idle([("zzz", 9999.0, 0)]))
    assert client.sets == []
