# 13: Benchmark the optimization levers

**What to build:** Each vLLM optimization lever is measured alone against the baseline, then the best lossless combination is chosen and deployed.

**Blocked by:** 12

**Status:** ready-for-agent

**Test status:** measured on WSL2 on 2026-11-13: `baseline`, `deployed`, `spec_ngram`, `spec_draft`, `compile`, and `awq` (numbers in `docs/benchmarks.md`). Not measured: `sched`, `kv_fp8`, and `min_latency`. They use a utilization of 0.92, and vLLM does not start because the free VRAM at start is 10.79 GiB (0.92 needs 11.03 GiB). No configuration turns prefix caching off, so its own effect is not measured. The final flag set waits for the owner.

- [ ] Configurations measured one at a time (`bench/levers.py`): AWQ, scheduler sizing, fp8 KV cache, n-gram and draft-model speculative decoding, compile mode, and the combination `min_latency`. Prefix caching is measured with the shared-prefix workload
- [ ] For each lever: latency, throughput, VRAM, and quality result in the benchmarks document
- [ ] Final flag set chosen with the reasons written down
- [ ] The vLLM Deployment uses the final flags; the chat completion smoke check still passes
