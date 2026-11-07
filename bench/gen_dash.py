#!/usr/bin/env python3
"""Generate the Grafana serving dashboard as a Kubernetes ConfigMap.

Edit this script, then run it from the repository root:

    python3 bench/gen_dash.py > k8s/monitoring/31-dashboard-serving.yaml

Then raise the checksum/dashboard annotation in 30-grafana.yaml and apply both files.
Metric names come from vLLM v0.28.0 (vllm/v1/metrics/loggers.py).
"""
import json

DS = {"type": "prometheus", "uid": "prometheus"}
M = 'model_name!=""'  # keeps every vLLM query on the real model series

panels = []
_id = [0]
_y = [0]


def _next_id():
    _id[0] += 1
    return _id[0]


def row(title):
    panels.append({
        "id": _next_id(), "type": "row", "title": title, "collapsed": False,
        "gridPos": {"x": 0, "y": _y[0], "w": 24, "h": 1}, "panels": [],
    })
    _y[0] += 1


def ts(title, targets, x, w=8, h=8, unit="short", desc="", ymax=None, stack=False):
    """One time series panel. targets is a list of (expr, legend)."""
    defaults = {
        "unit": unit,
        "custom": {
            "drawStyle": "line", "lineWidth": 1, "fillOpacity": 12,
            "showPoints": "never", "spanNulls": True,
            "stacking": {"mode": "normal" if stack else "none", "group": "A"},
        },
    }
    if ymax is not None:
        defaults["max"] = ymax
        defaults["min"] = 0
    panels.append({
        "id": _next_id(), "type": "timeseries", "title": title, "description": desc,
        "datasource": DS,
        "gridPos": {"x": x, "y": _y[0], "w": w, "h": h},
        "fieldConfig": {"defaults": defaults, "overrides": []},
        "options": {
            "legend": {"displayMode": "list", "placement": "bottom"},
            "tooltip": {"mode": "multi"},
        },
        "targets": [
            {"refId": chr(65 + i), "expr": e, "legendFormat": lg, "datasource": DS}
            for i, (e, lg) in enumerate(targets)
        ],
    })


def end_line():
    _y[0] += 8


def quantiles(metric, label_filter=M, rng="$__rate_interval"):
    return [
        (f'histogram_quantile(0.5, sum by (le) (rate({metric}_bucket{{{label_filter}}}[{rng}])))', "p50"),
        (f'histogram_quantile(0.99, sum by (le) (rate({metric}_bucket{{{label_filter}}}[{rng}])))', "p99"),
    ]


# ---------------------------------------------------------------- SLO
row("SLO - latency and throughput")
ts("TTFT (time to first token)", quantiles("vllm:time_to_first_token_seconds"), 0, unit="s",
   desc="Prefill latency. The time until the first token streams back.")
ts("TPOT (time per output token)", quantiles("vllm:request_time_per_output_token_seconds"), 8, unit="s",
   desc="Decode speed per request. Lower is better.")
ts("E2E request latency", quantiles("vllm:e2e_request_latency_seconds"), 16, unit="s")
end_line()
ts("Throughput (tokens/s)", [
    (f'sum(rate(vllm:generation_tokens_total{{{M}}}[$__rate_interval]))', "generation"),
    (f'sum(rate(vllm:prompt_tokens_total{{{M}}}[$__rate_interval]))', "prompt"),
], 0, unit="short")
ts("Finish reasons (requests/s)", [
    (f'sum by (finished_reason) (rate(vllm:request_success_total{{{M}}}[$__rate_interval]))', "{{finished_reason}}"),
], 8, unit="reqps", desc="stop is normal. length means the answer hit the token limit. abort means the client left.")
ts("Queue time", quantiles("vllm:request_queue_time_seconds"), 16, unit="s",
   desc="Time a request waits before the engine starts it.")
end_line()

# ---------------------------------------------------------------- saturation
row("Saturation - KV cache, batching, preemptions")
ts("KV cache usage", [(f'vllm:kv_cache_usage_perc{{{M}}} * 100', "KV cache")], 0, unit="percent", ymax=100,
   desc="Near 100 percent means new requests wait or running requests get preempted.")
ts("Running vs waiting requests", [
    (f'vllm:num_requests_running{{{M}}}', "running"),
    (f'vllm:num_requests_waiting{{{M}}}', "waiting"),
], 8)
ts("Preemptions (per second)", [
    (f'sum(rate(vllm:num_preemptions_total{{{M}}}[$__rate_interval]))', "preemptions"),
], 16, desc="Each preemption throws away KV cache and recomputes it. It should stay at zero.")
end_line()
ts("Prefix cache hit rate", [
    (f'sum(rate(vllm:prefix_cache_hits_total{{{M}}}[$__rate_interval])) / '
     f'sum(rate(vllm:prefix_cache_queries_total{{{M}}}[$__rate_interval])) * 100', "hit rate"),
], 0, unit="percent", ymax=100)
ts("Batch size (tokens per iteration)", [
    (f'sum(rate(vllm:iteration_tokens_total_sum{{{M}}}[$__rate_interval])) / '
     f'sum(rate(vllm:iteration_tokens_total_count{{{M}}}[$__rate_interval]))', "avg tokens/iteration"),
], 8)
ts("Speculative decoding acceptance", [
    (f'sum(rate(vllm:spec_decode_num_accepted_tokens_total{{{M}}}[$__rate_interval])) / '
     f'sum(rate(vllm:spec_decode_num_draft_tokens_total{{{M}}}[$__rate_interval])) * 100', "acceptance"),
], 16, unit="percent", ymax=100, desc="Empty when speculative decoding is off.")
end_line()

# ---------------------------------------------------------------- GPU
row("GPU")
ts("GPU temperature", [("DCGM_FI_DEV_GPU_TEMP", "{{gpu}}")], 0, unit="celsius")
ts("GPU utilization", [("DCGM_FI_DEV_GPU_UTIL", "{{gpu}}")], 8, unit="percent", ymax=100)
ts("GPU power", [("DCGM_FI_DEV_POWER_USAGE", "{{gpu}}")], 16, unit="watt")
end_line()
ts("VRAM", [
    ("DCGM_FI_DEV_FB_USED", "used"),
    ("DCGM_FI_DEV_FB_FREE", "free"),
], 0, unit="decmbytes", stack=True,
   desc="The desktop display also uses this memory on the PC.")
ts("Clocks", [
    ("DCGM_FI_DEV_SM_CLOCK", "SM"),
    ("DCGM_FI_DEV_MEM_CLOCK", "memory"),
], 8, unit="rotmhz")
end_line()

# ---------------------------------------------------------------- node and pods
row("Node and pods")
ts("CPU usage", [
    ('100 - avg(rate(node_cpu_seconds_total{mode="idle"}[$__rate_interval])) * 100', "CPU"),
], 0, unit="percent", ymax=100)
ts("RAM used", [
    ('(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100', "RAM"),
], 8, unit="percent", ymax=100)
ts("Disk used (root filesystem)", [
    ('(1 - node_filesystem_avail_bytes{mountpoint="/",fstype!="rootfs"} / '
     'node_filesystem_size_bytes{mountpoint="/",fstype!="rootfs"}) * 100', "/"),
], 16, unit="percent", ymax=100)
end_line()
ts("Pod phase", [
    ('sum by (namespace, phase) (kube_pod_status_phase == 1)', "{{namespace}} {{phase}}"),
], 0, w=12, desc="Count of pods per phase.")
ts("Container restarts (last hour)", [
    ('sum by (namespace, pod) (increase(kube_pod_container_status_restarts_total[1h]))', "{{namespace}}/{{pod}}"),
], 12, w=12)
end_line()

# ---------------------------------------------------------------- speech
row("Speech (STT and TTS)")
ts("Request rate", [
    ('sum(rate(stt_requests_total[$__rate_interval]))', "STT"),
    ('sum(rate(tts_requests_total[$__rate_interval]))', "TTS"),
], 0, w=8, unit="reqps")
ts("STT latency", quantiles("stt_request_duration_seconds", label_filter=""), 8, w=8, unit="s")
ts("TTS latency", quantiles("tts_request_duration_seconds", label_filter=""), 16, w=8, unit="s")
end_line()

dashboard = {
    "id": None, "uid": "vllm-serving", "title": "vLLM Serving - SLO, KV cache, GPU",
    "tags": ["vllm", "gpu", "serving"], "timezone": "browser", "schemaVersion": 39,
    "version": 1, "editable": True, "refresh": "10s",
    "time": {"from": "now-1h", "to": "now"},
    "templating": {"list": []},
    "annotations": {"list": []},
    "panels": panels,
}

body = json.dumps(dashboard, indent=2)
indented = "\n".join("    " + line for line in body.splitlines())
print("""# Grafana dashboard "vLLM Serving - SLO, KV cache, GPU" (uid: vllm-serving).
# Generated by bench/gen_dash.py. Edit that script and run it again. Do not edit this file.
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard-serving
  namespace: monitoring
data:
  serving.json: |""")
print(indented)
