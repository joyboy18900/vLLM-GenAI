import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from scoring import (
    PodState,
    Weights,
    choose_pod,
    parse_vllm_metrics,
    prefix_key,
    score,
    weights_from_env,
)

METRICS = """\
# HELP vllm:num_requests_running Number of requests in model execution batches.
# TYPE vllm:num_requests_running gauge
vllm:num_requests_running{engine="0",model_name="Qwen/Qwen2.5-3B-Instruct"} 3.0
# TYPE vllm:num_requests_waiting gauge
vllm:num_requests_waiting{engine="0",model_name="Qwen/Qwen2.5-3B-Instruct"} 2.0
# TYPE vllm:kv_cache_usage_perc gauge
vllm:kv_cache_usage_perc{engine="0",model_name="Qwen/Qwen2.5-3B-Instruct"} 0.25
# TYPE vllm:prefix_cache_queries_total counter
vllm:prefix_cache_queries_total{engine="0",model_name="Qwen/Qwen2.5-3B-Instruct"} 1000.0
# TYPE vllm:prefix_cache_hits_total counter
vllm:prefix_cache_hits_total{engine="0",model_name="Qwen/Qwen2.5-3B-Instruct"} 400.0
"""


def pod(name, waiting=0, running=0, in_flight=0, kv=0.0, prefixes=(), ready=True):
    return PodState(name=name, ready=ready, waiting=waiting, running=running,
                    in_flight=in_flight, kv_usage=kv, prefixes=frozenset(prefixes))


W = Weights(prefix_bonus=3.0, queue=1.0, kv=2.0)


# parse_vllm_metrics

def test_parse_reads_the_five_metrics():
    m = parse_vllm_metrics(METRICS)
    assert m.running == 3.0
    assert m.waiting == 2.0
    assert m.kv_usage == 0.25
    assert m.prefix_queries == 1000.0
    assert m.prefix_hits == 400.0


def test_parse_sums_values_of_several_label_sets():
    text = ('vllm:num_requests_waiting{engine="0"} 1.0\n'
            'vllm:num_requests_waiting{engine="1"} 4.0\n')
    assert parse_vllm_metrics(text).waiting == 5.0


def test_parse_ignores_comments_and_unknown_lines():
    text = "# comment\nother_metric 9\nvllm:num_requests_running 1\n"
    assert parse_vllm_metrics(text).running == 1.0


def test_parse_missing_metric_is_zero():
    m = parse_vllm_metrics("vllm:num_requests_running 1\n")
    assert m.waiting == 0.0 and m.kv_usage == 0.0


def test_parse_empty_text_raises():
    with pytest.raises(ValueError):
        parse_vllm_metrics("")


def test_parse_text_without_any_vllm_metric_raises():
    with pytest.raises(ValueError):
        parse_vllm_metrics("# only a comment\nother_metric 9\n")


# prefix_key

def msgs(system, user):
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def test_prefix_key_is_the_same_for_the_same_start():
    a = prefix_key(msgs("S", "hello world " * 50 + "A"), 20)
    b = prefix_key(msgs("S", "hello world " * 50 + "B"), 20)
    assert a == b


def test_prefix_key_differs_for_another_system_prompt():
    assert prefix_key(msgs("S1", "hi"), 20) != prefix_key(msgs("S2", "hi"), 20)


def test_prefix_key_differs_for_another_start_of_the_user_message():
    assert prefix_key(msgs("S", "aaa"), 20) != prefix_key(msgs("S", "bbb"), 20)


def test_prefix_key_works_without_a_system_message():
    assert prefix_key([{"role": "user", "content": "hi"}], 20)


def test_prefix_key_reads_text_parts_of_a_list_content():
    parts = [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]
    plain = [{"role": "user", "content": "hi"}]
    assert prefix_key(parts, 20) == prefix_key(plain, 20)


def test_prefix_key_for_no_messages_is_a_fixed_value():
    assert prefix_key([], 20) == prefix_key([], 20)


# score and choose_pod

def test_score_has_no_queue_penalty_for_an_idle_pod():
    assert score(pod("a"), "k", W) == 0.0


def test_score_counts_waiting_running_and_in_flight_as_queue():
    assert score(pod("a", waiting=1, running=2, in_flight=3), "k", W) == -6.0


def test_score_penalizes_kv_usage():
    assert score(pod("a", kv=0.5), "k", W) == -1.0


def test_score_gives_a_bonus_for_a_known_prefix():
    assert score(pod("a", prefixes={"k"}), "k", W) == 3.0


def test_choose_prefers_the_shorter_queue():
    best = choose_pod([pod("a", waiting=5), pod("b", waiting=1)], "k", W)
    assert best.name == "b"


def test_choose_prefers_the_lower_kv_usage():
    best = choose_pod([pod("a", kv=0.9), pod("b", kv=0.1)], "k", W)
    assert best.name == "b"


def test_choose_prefers_the_pod_with_the_prefix_when_load_is_equal():
    best = choose_pod([pod("a"), pod("b", prefixes={"k"})], "k", W)
    assert best.name == "b"


def test_a_long_queue_beats_the_prefix_bonus():
    busy = pod("a", waiting=10, prefixes={"k"})
    assert choose_pod([busy, pod("b")], "k", W).name == "b"


def test_choose_skips_pods_that_are_not_ready():
    best = choose_pod([pod("a", ready=False), pod("b", waiting=9)], "k", W)
    assert best.name == "b"


def test_choose_returns_none_when_no_pod_is_ready():
    assert choose_pod([pod("a", ready=False)], "k", W) is None
    assert choose_pod([], "k", W) is None


def test_tie_goes_to_the_first_name_in_sort_order():
    assert choose_pod([pod("b"), pod("a")], "k", W).name == "a"
    assert choose_pod([pod("a"), pod("b")], "k", W).name == "a"


# weights_from_env

def test_weights_have_defaults():
    w = weights_from_env({})
    assert w == Weights(prefix_bonus=3.0, queue=1.0, kv=2.0)


def test_weights_read_the_environment():
    w = weights_from_env({"ROUTER_W_PREFIX": "5", "ROUTER_W_QUEUE": "0.5", "ROUTER_W_KV": "1"})
    assert w == Weights(prefix_bonus=5.0, queue=0.5, kv=1.0)


def test_weights_reject_a_bad_value():
    with pytest.raises(ValueError):
        weights_from_env({"ROUTER_W_QUEUE": "abc"})
