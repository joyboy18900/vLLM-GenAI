# Benchmarks

Each number here comes from a vLLM log line, from `nvidia-smi`, or from a script. Do not type
numbers by hand. Every result says where it was measured. The first runs are on WSL2, so the label
is "WSL2". They do not replace the runs on Ubuntu or EC2.

## Test setup

| Item | Value |
|---|---|
| Machine | The local PC (Ryzen 7 8700F, 32 GB RAM) in WSL2 (Ubuntu 24.04, 24 GB limit) on Windows |
| GPU and driver version | RTX 4070 SUPER 12 GB. Windows driver 616.64, driver seen in WSL2 615.65.07, CUDA 13.4 |
| vLLM version | v0.28.0 (`vllm/vllm-openai:v0.28.0`) |
| Model and dtype | `Qwen/Qwen2.5-3B-Instruct`, float16 |
| Flags | the arguments of `k8s/vllm-deployment.yaml` (configuration `deployed` in `bench/levers.py`) |

## VRAM (ticket 02)

### Qwen2.5-3B-Instruct, fp16 (WSL2, k3s pod)

Measured on 2026-11-13 in the k3s pod, with the flags of `k8s/vllm-deployment.yaml` (utilization
0.80, max-model-len 8192, max-num-seqs 16). The model was in the cache already (see "Download the
model first" in `docs/setup.md`). The standalone run of ticket 02 is not done.

| Item | Value | Source |
|---|---|---|
| Desktop display, before vLLM | 799 MiB | `nvidia-smi` |
| Checkpoint size | 5.75 GiB | vLLM log: "Checkpoint size" |
| Weights in VRAM | 5.79 GiB | vLLM log: "Model loading took" |
| KV cache, first start (empty compile cache) | 2.26 GiB, 65,920 tokens, 8.05x concurrency for 8,192 tokens | vLLM log |
| KV cache, next start (compile cache present) | 3.26 GiB, 94,976 tokens, 11.59x concurrency for 8,192 tokens | vLLM log |
| Total VRAM in use, vLLM idle (next start) | 11,038 MiB of 12,282 MiB (this includes the desktop) | `nvidia-smi` |
| Time to ready, first start / next start | about 72 s / about 51 s (torch.compile: 12.22 s / 0.28 s) | polling the pod, vLLM log |

The first start has less KV cache because the compile step uses more memory: 6.55 GiB of non-torch
memory and 0.78 GiB of peak activation, against 5.99 GiB and 0.35 GiB on the next start. Use the
second row for planning. The KV cache is 3.5 times the 0.92 GiB of the earlier try below.

The download of the model (a one-time step) took 5 minutes 25 seconds. The first try inside the pod
ran at about 2 MB/s and did not finish in the 10-minute startup window, so the pod was restarted by
the startup probe.

### Earlier try: Qwen3.5-4B (WSL2)

The first model was Qwen3.5-4B in bf16. It did not leave much KV cache on this 12 GB GPU, and the
model was changed. The numbers stay here as a record.

| Item | Value | Source |
|---|---|---|
| Desktop display, before vLLM | 1,067 MiB (later reads between 403 and 1,085 MiB) | `nvidia-smi` |
| Weights, text-only | 7.99 GiB (8.61 GiB with the vision encoder) | vLLM log: "Model loading took" |
| KV cache at utilization 0.89 | 0.92 GiB, 16,384 tokens, 4.00x concurrency for 4,096 tokens | vLLM log |
| Utilization 0.80 | KV cache memory is -0.15 GiB. vLLM does not start. | vLLM log |
| Total VRAM in use, vLLM idle | 10,541 MiB of 12,282 MiB (this includes the desktop) | `nvidia-smi` |

The checks of that run passed: `/v1/models`, a chat completion (normal and stream), and a tool call.

## Baseline (ticket 12)

Not measured yet. Run these commands, then paste the table here:

```bash
bench/run.sh baseline
python3 bench/summarize.py baseline
python3 bench/quality_check.py --label baseline
```

## Optimization levers (ticket 13)

Not measured yet. One section per lever: latency, throughput, VRAM, and the quality result.
The configurations are: `baseline`, `awq`, `sched`, `kv_fp8`, `spec_ngram`, `spec_draft`, `compile`,
`deployed`, and `min_latency`. Run them with `bench/levers.py` (see `docs/setup.md`, section
"Optimization levers").

Final choice: not made yet. Write the chosen flags and the reasons here.

## Voice (ticket 06)

Not measured yet. The time from the end of speech to the first audio.

## Thai TTS (ticket 18, bonus)

Candidates. The facts come from the model cards and the project pages. Time and quality are not
measured yet (see `docs/setup.md`, section "Thai TTS").

| Item | Piper `th_TH-tsync2-medium` | FastThaiG2P (Thai Kokoro-82M, ONNX) |
|---|---|---|
| Runs on | CPU | CPU |
| Size | 63 MB | about 326 MB |
| Sample rate | 22.05 kHz | not checked |
| License of the code | GPL-3.0 (`piper-tts` 1.8.0, from PyPI and the repository) | Apache-2.0 |
| License of the voice data or weights | CC BY-NC-SA 3.0, non-commercial (from the model card of the voice) | not stated in the release notes or the README |
| Needs | Piper 1.8 or newer (we use 1.8.0) | a new server in this repository |
| Time to first audio | not measured yet | not measured yet |
| RTF | not measured yet | not measured yet (the authors state about 0.2 on the CPU) |
| Listening result | not heard yet | not heard yet |

Chosen voice: not chosen yet.

