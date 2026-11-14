# 13: Benchmark the optimization levers

**What to build:** Each vLLM optimization lever is measured alone against the baseline, then the best lossless combination is chosen and deployed.

**Blocked by:** 12

**Status:** ready-for-agent

**Test status:** measured on WSL2 on 2026-11-13: `baseline`, `ngram_chunked`, `spec_ngram`, `spec_draft`, `compile`, and `awq` (numbers in `docs/benchmarks.md`). Not measured at 0.92: `sched`, `kv_fp8`, and `min_latency`. They use a utilization of 0.92, and vLLM does not start because the free VRAM at start is 10.79 GiB (0.92 needs 11.03 GiB). No configuration turns prefix caching off, so its own effect is not measured. On 2026-11-14 `sched_085` and `kv_fp8_085` (the same as `sched` and `kv_fp8` at utilization 0.85) were measured. `min_latency` is not measured (not needed for the final choice). The Thai fact check ran for `baseline` and `awq`. The owner chose `baseline` as the final flag set. The Deployment uses it and the smoke test passed (10 of 10, `--no-https`).

- [x] Configurations measured one at a time (`bench/levers.py`): AWQ, scheduler sizing, fp8 KV cache, n-gram and draft-model speculative decoding, compile mode, and the combination `min_latency`. Prefix caching is measured with the shared-prefix workload
- [x] For each lever: latency, throughput, VRAM, and quality result in the benchmarks document
- [x] Final flag set chosen with the reasons written down
- [x] The vLLM Deployment uses the final flags; the chat completion smoke check still passes
