# 01: Measure two AWQ pods on one GPU

**What to build:** Two AWQ vLLM pods run at the same time on the one GPU. The real VRAM use and the KV cache of each pod are measured and written down before any router manifest is written.

**Blocked by:** None (can start when the PC is on)

**Status:** ready-for-agent

**Test status:** not started.

- [ ] Two Deployments, `vllm-awq-a` and `vllm-awq-b`, each with a share of `--gpu-memory-utilization`, start one after the other and both become ready (the fp16 `baseline` pod is scaled to zero first)
- [ ] VRAM of each pod, KV cache (tokens and concurrency), and the VRAM left on the GPU are recorded in `docs/benchmarks.md`
- [ ] The result says if a third pod fits, and the shares that were tested
- [ ] The label of the pods matches the `vllm` job of Prometheus, and both targets are up
- [ ] The setup runbook has the commands and the check steps
