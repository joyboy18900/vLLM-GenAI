# 02: vLLM standalone on the PC

**What to build:** vLLM serves Qwen2.5-3B-Instruct directly on the PC (outside Kubernetes). A `curl` chat completion returns an answer. The real VRAM use is measured and replaces the estimates in CLAUDE.md.

**Blocked by:** 01

**Status:** ready-for-agent

**Test status:** ran on WSL2 on 2026-11-08 with an earlier model (Qwen3.5-4B). On 2026-11-13, Qwen2.5-3B-Instruct ran in the k3s pod (not standalone, see ticket 03). Its weights and KV cache are in `docs/benchmarks.md`. The standalone run is not done, so no box is ticked.

- [ ] vLLM version pinned, Qwen2.5-3B-Instruct served in fp16 through the OpenAI-compatible API
- [ ] Tool calling enabled with the hermes parser
- [ ] `curl` to `/v1/models` lists the model, and `curl` to `/v1/chat/completions` returns a non-empty answer (stream and non-stream)
- [ ] VRAM measured: weights, KV cache size (tokens and max concurrency from the vLLM log), desktop display use
- [ ] If the KV cache is too small, the fp8 KV cache or AWQ is tested and the choice is recorded
- [ ] The VRAM budget table in CLAUDE.md shows the measured numbers
- [ ] The setup runbook and the benchmarks document record the commands and numbers
- [ ] The standalone process is stopped and the GPU is free at the end
