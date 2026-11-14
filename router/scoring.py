"""Pod choice for the router. No I/O: every function takes plain values and returns plain values."""
import hashlib
import re
from dataclasses import dataclass

# Metric names that the router reads from the /metrics text of a vLLM pod.
_FIELDS = {
    "vllm:num_requests_running": "running",
    "vllm:num_requests_waiting": "waiting",
    "vllm:kv_cache_usage_perc": "kv_usage",
    "vllm:prefix_cache_queries_total": "prefix_queries",
    "vllm:prefix_cache_hits_total": "prefix_hits",
}
# Characters of the first user message that go into the prefix key (chosen in ticket 02).
PREFIX_CHARS = 200
_LINE = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{[^}]*\})?\s+(\S+)")


@dataclass(frozen=True)
class PodMetrics:
    running: float = 0.0
    waiting: float = 0.0
    kv_usage: float = 0.0
    prefix_queries: float = 0.0
    prefix_hits: float = 0.0


@dataclass(frozen=True)
class PodState:
    name: str
    ready: bool
    waiting: float
    running: float
    in_flight: float  # requests that the router sent and did not finish
    kv_usage: float
    prefixes: frozenset  # prefix keys that this pod served before


@dataclass(frozen=True)
class Weights:
    prefix_bonus: float = 3.0
    queue: float = 1.0
    kv: float = 2.0


def parse_vllm_metrics(text):
    """Read the five vLLM metrics. A value with several label sets is the sum. Raises ValueError
    when the text has none of them (a wrong page or an empty answer)."""
    totals = {}
    for line in text.splitlines():
        m = _LINE.match(line)
        if not m or m.group(1) not in _FIELDS:
            continue
        field = _FIELDS[m.group(1)]
        totals[field] = totals.get(field, 0.0) + float(m.group(2))
    if not totals:
        raise ValueError("no vLLM metric in the text")
    return PodMetrics(**totals)


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return ""


def prefix_key(messages, n_chars):
    """Hash of the system prompt and the first n_chars of the first user message."""
    system = next((_text_of(m.get("content")) for m in messages if m.get("role") == "system"), "")
    user = next((_text_of(m.get("content")) for m in messages if m.get("role") == "user"), "")
    raw = system + "\x00" + user[:n_chars]
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def score(pod, key, weights):
    queue = pod.waiting + pod.running + pod.in_flight
    bonus = weights.prefix_bonus if key in pod.prefixes else 0.0
    return bonus - weights.queue * queue - weights.kv * pod.kv_usage


def choose_pod(pods, key, weights):
    """The ready pod with the best score, or None. A tie goes to the first name in sort order."""
    ready = sorted((p for p in pods if p.ready), key=lambda p: p.name)
    if not ready:
        return None
    return max(ready, key=lambda p: score(p, key, weights))  # max keeps the first of equal scores


def weights_from_env(env):
    def read(name, default):
        return float(env.get(name, default))

    return Weights(
        prefix_bonus=read("ROUTER_W_PREFIX", 3.0),
        queue=read("ROUTER_W_QUEUE", 1.0),
        kv=read("ROUTER_W_KV", 2.0),
    )
