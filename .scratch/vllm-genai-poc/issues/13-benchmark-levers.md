# 13: Benchmark the optimization levers

**What to build:** Each vLLM optimization lever is measured alone against the baseline, then the best lossless combination is chosen and deployed.

**Blocked by:** 12

**Status:** ready-for-agent

**Test status:** written, untested. `bench/levers.py` builds the flags of each lever (checked offline against the v0.28.0 argument names). No measurement and no final flag set yet.

- [ ] Configurations measured one at a time (`bench/levers.py`): AWQ, scheduler sizing, fp8 KV cache, n-gram and draft-model speculative decoding, compile mode, and the combination `min_latency`. Prefix caching is measured with the shared-prefix workload
- [ ] For each lever: latency, throughput, VRAM, and quality result in the benchmarks document
- [ ] Final flag set chosen with the reasons written down
- [ ] The vLLM Deployment uses the final flags; the chat completion smoke check still passes
