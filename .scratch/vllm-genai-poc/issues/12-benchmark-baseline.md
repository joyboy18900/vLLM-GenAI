# 12: Benchmark harness and baseline

**What to build:** One command runs `vllm bench serve` against the vLLM Service for a set of workloads and concurrency levels, saves the raw results, and writes a summary table. Baseline numbers are recorded.

**Blocked by:** 03

**Status:** ready-for-agent

**Test status:** written, untested on the cluster. The summary and quality scripts ran against fake data on a Mac. The `vllm bench serve` flags were read from the v0.28.0 source. No baseline numbers exist yet.

- [ ] Workloads: random input/output (engine only), real chat text, shared long prefix (prefix caching)
- [ ] Concurrency 1, 8, and 16, with warmup and a fixed seed
- [ ] Fixed quality prompt set (English and Thai) checked at temperature 0
- [ ] Raw results saved, summary table generated from them (no hand-typed numbers)
- [ ] Baseline (bf16, default flags) recorded in the benchmarks document with vLLM version, driver, model, and flags
