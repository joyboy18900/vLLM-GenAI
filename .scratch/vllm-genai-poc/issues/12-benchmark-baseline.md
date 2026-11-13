# 12: Benchmark harness and baseline

**What to build:** One command runs `vllm bench serve` against the vLLM Service for a set of workloads and concurrency levels, saves the raw results, and writes a summary table. Baseline numbers are recorded.

**Blocked by:** 03

**Status:** ready-for-agent

**Test status:** ran on WSL2 on 2026-11-13 (6 configurations, 8 runs each, no failed request). The run found a bug in `bench/run.sh`: the `custom` dataset needs pandas, which the vLLM image does not have. The `chat` workload now uses a `sharegpt` dataset (fixed in the commit "read the chat prompts as a ShareGPT dataset"). The numbers are in `docs/benchmarks.md`. The quality check exits with 1 when a Thai prompt fails, and 3 of 6 Thai prompts pass in the baseline, so read the answers, not the exit code.

- [x] Workloads: random input/output (engine only), real chat text, shared long prefix (prefix caching)
- [x] Concurrency 1, 8, and 16, with warmup and a fixed seed
- [x] Fixed quality prompt set (English and Thai) checked at temperature 0
- [x] Raw results saved, summary table generated from them (no hand-typed numbers)
- [x] Baseline (fp16, plain engine flags) recorded in the benchmarks document with vLLM version, driver, model, and flags
