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
| Flags | one argument list per configuration of `bench/levers.py`. The configuration `deployed` equals `k8s/vllm-deployment.yaml` (now the same as `baseline`). The VRAM section below was measured with `ngram_chunked`, the earlier Deployment |

## VRAM (ticket 02)

### Qwen2.5-3B-Instruct, fp16 (WSL2, k3s pod)

Measured on 2026-11-13 in the k3s pod, with the flags of the earlier Deployment (`ngram_chunked`, utilization
0.80, max-model-len 8192, max-num-seqs 16). The model was in the cache already (see "Download the
model first" in `docs/setup.md`).

| Item | Value | Source |
|---|---|---|
| Desktop display, before vLLM | 799 MiB (k3s start), 1,169 MiB (standalone start, later the same day) | `nvidia-smi` |
| Checkpoint size | 5.75 GiB | vLLM log: "Checkpoint size" |
| Weights in VRAM | 5.79 GiB | vLLM log: "Model loading took" |
| KV cache, first start (empty compile cache) | 2.26 GiB, 65,920 tokens, 8.05x concurrency for 8,192 tokens | vLLM log |
| KV cache, next start (compile cache present) | 3.26 GiB, 94,976 tokens, 11.59x concurrency for 8,192 tokens | vLLM log |
| Total VRAM in use, vLLM idle (next start) | 11,038 MiB of 12,282 MiB (this includes the desktop) | `nvidia-smi` |
| Time to ready, first start / next start | about 72 s / about 51 s (torch.compile: 12.22 s / 0.28 s) | polling the pod, vLLM log |

The first start has less KV cache because the compile step uses more memory: 6.55 GiB of non-torch
memory and 0.78 GiB of peak activation, against 5.99 GiB and 0.35 GiB on the next start. Use the
second row for planning. The KV cache is 3.5 times the 0.92 GiB of the earlier try below.

The standalone run in Docker (ticket 02, same flags, same cache folder) gave the same numbers: weights
5.79 GiB, KV cache 3.26 GiB, 94,976 tokens, 11.59x concurrency, 11,102 MiB in use at idle. It was
ready in 61 s. The desktop display used 1,169 MiB at that start, 370 MiB more than at the first
start. vLLM still saw 10.79 GiB of free VRAM in both starts.

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

Measured on 2026-11-13 on WSL2 (k3s pod, `vllm bench serve` inside the pod, seed 0, 3 warmup requests,
`--ignore-eos`). The monitoring stack ran at the same time, as in normal use. The configuration is
`baseline` of `bench/levers.py` (fp16, utilization 0.85, max-model-len 8192, max-num-seqs 16, prefix
caching, no speculative decoding).

The engine needs `VLLM_USE_V2_MODEL_RUNNER=0` on WSL2 for every configuration without speculative
decoding. Without it, vLLM v0.28.0 starts the model runner V2 and stops with
`RuntimeError: UVA is not available`. The variable was set on the Deployment during the runs and
removed after them. The configuration with n-gram decoding chooses the runner V1 by itself.

Each table row is `vllm bench serve` output. TTFT and TPOT are in milliseconds. Workload `random` is
random tokens (input 512, output 128), `chat` is the 28 prompts of `bench/prompts` (output 128), and
`prefix` is a shared prefix of 1024 tokens (input 256, output 128).

| workload | conc | TTFT p50 (ms) | TTFT p99 (ms) | TPOT p50 (ms) | TPOT p99 (ms) | out tok/s | req/s | done | failed |
|---|---|---|---|---|---|---|---|---|---|
| chat | 1 | 22.0 | 23.2 | 14.2 | 14.3 | 70.7 | 0.6 | 24 | 0 |
| chat | 8 | 46.2 | 49.9 | 14.5 | 14.8 | 539.1 | 4.2 | 96 | 0 |
| chat | 16 | 52.1 | 81.5 | 15.0 | 15.2 | 1047.2 | 8.2 | 160 | 0 |
| prefix | 1 | 36.7 | 47.4 | 14.1 | 14.7 | 70.1 | 0.5 | 24 | 0 |
| prefix | 8 | 148.5 | 213.8 | 15.3 | 16.3 | 487.3 | 3.8 | 96 | 0 |
| random | 1 | 57.1 | 60.1 | 14.1 | 14.7 | 69.0 | 0.5 | 24 | 0 |
| random | 8 | 214.1 | 389.4 | 15.4 | 17.2 | 471.3 | 3.7 | 96 | 0 |
| random | 16 | 423.3 | 718.7 | 18.0 | 20.7 | 760.8 | 5.9 | 160 | 0 |

Start of the baseline: weights 5.79 GiB, KV cache 2.97 GiB (86,560 tokens, 10.57x concurrency for 8,192 tokens), 10818 MiB of VRAM in use at idle, ready in 62 s. Preemptions during the run: 0.

Quality check (temperature 0, 256 tokens): English 8/8, Thai 3/6 prompts contain the expected word. The Thai result is a property of the model. It is the reference for the other configurations.

## Optimization levers (ticket 13)

Each configuration is a full argument list in `bench/levers.py`. The runs used the same harness and
the same seed as the baseline. Workload `chat` is the closest to the product. Workload `random`
uses random tokens, so use it for the engine only.

### Overview

| Configuration | Util | Weights (GiB) | KV cache (GiB, tokens, concurrency) | VRAM idle (MiB) | Ready (s) | chat out tok/s, conc 1 / 8 / 16 | chat TPOT p50 (ms), conc 1 | Same answers as baseline | Quality pass |
|---|---|---|---|---|---|---|---|---|---|
| `baseline` | 0.85 | 5.79 | 2.97, 86,560, 10.57x | 10818 | 62 | 70.7 / 539.1 / 1047.2 | 14.2 | 14/14 | 11/14 |
| `ngram_chunked` | 0.80 | 5.79 | 3.26, 94,976, 11.59x | 11198 | 52 | 65.0 / 464.8 / 851.9 | 15.6 | 14/14 | 11/14 |
| `spec_ngram` | 0.85 | 5.79 | 3.86, 112,448, 13.73x | 11769 | 51 | 64.5 / 449.6 / 826.2 | 15.8 | 14/14 | 11/14 |
| `spec_draft` | 0.85 | 6.73 | 1.88, 40,992, 5.00x | 10560 | 71 | 80.7 / 548.6 / 987.6 | 11.7 | 14/14 | 11/14 |
| `compile` | 0.85 | 5.79 | 3.97, 115,632, 14.12x | 11607 | 51 | 68.7 / 529.3 / 1028.6 | 14.5 | 14/14 | 11/14 |
| `awq` | 0.85 | 1.95 | 6.89, 200,736, 24.50x | 10704 | 71 | 165.2 / 1256.2 / 2345.5 | 6.0 | 10/14 | 12/14 |
| `sched_085` | 0.85 | 5.79 | 103,840 tokens, 25.35x (4,096 per request) | n/a | n/a | 68.4 / 528.4 / 528.2 | 14.6 | 14/14 | 11/14 |
| `kv_fp8_085` | 0.85 | 5.79 | 183,232 tokens, 44.73x (4,096 per request) | n/a | n/a | 69.0 / 527.4 / 534.0 | 14.4 | 10/14 | 11/14 |

The KV cache of one configuration changes with the start. The first start of a new argument list builds
the compile cache and leaves less KV cache (see "VRAM" above), and the utilization differs. Compare the
speed columns, and read the KV cache column only as the size that each start had.

The last two rows (`sched_085`, `kv_fp8_085`) were measured on 2026-11-14 with the workloads `random`, `chat`, and `prefix`. Their VRAM idle and start time were not recorded, and the KV cache is given in tokens and for 4,096 tokens per request (`max-model-len` 4096).

### Configurations that did not start

| Configuration | Utilization | Result |
|---|---|---|
| `sched` | 0.92 | Stopped at start: `Free memory on device cuda:0 (10.79/11.99 GiB) on startup is less than desired GPU memory utilization (0.92, 11.03 GiB). Decrease GPU memory utilization or reduce GPU memory used by other processes.` |
| `kv_fp8` | 0.92 | Stopped at start. The same error as `sched` (the line was read by hand from the pod log, because the driver script did not save it). |
| `min_latency` | 0.92 | Stopped at start: `Free memory on device cuda:0 (10.79/11.99 GiB) on startup is less than desired GPU memory utilization (0.92, 11.03 GiB). Decrease GPU memory utilization or reduce GPU memory used by other processes.` |

vLLM refuses to start when the free VRAM is less than the utilization times the total VRAM. At every
start the free VRAM was 10.79 GiB of 11.99 GiB (8 starts with a log, and the three that stopped). This
was the same when the desktop used 799 MiB and when it used 1,169 MiB, so the desktop is not the whole
reason. The cause is not found. A utilization of 0.92 needs 11.03 GiB. These three configurations are
not measured at 0.92. `sched` and `kv_fp8` were measured at 0.85 as `sched_085` and `kv_fp8_085` (below). A utilization of 0.89 needs 10.67 GiB. It fits by calculation (not tested), with 0.12 GiB
to spare.

### What the numbers show

All values are from the tables on this page. Out tok/s is the output throughput.

- **N-gram decoding (`spec_ngram`) helps `random` and does not help `chat`.** TPOT p50 at concurrency 1: `random` 14.1 ms to 4.8 ms, `chat` 14.2 ms to 15.8 ms. Out tok/s of `chat`: -9% at concurrency 1, -17% at 8, -21% at 16. The answers are the same as the baseline (14 of 14). The vLLM log of every n-gram start says that async scheduling is turned off and that `max_num_scheduled_tokens` is set to 2048. This can be part of the cost. It is not tested alone.
- **`ngram_chunked` (the n-gram flags of the earlier Deployment, 0.80) behaves like `spec_ngram`.** Out tok/s of `chat` at concurrency 16: 851.9, against 1047.2 for the baseline.
- **A draft model (`spec_draft`) is faster at low concurrency and slower at high concurrency.** Out tok/s of `chat`: +14% at concurrency 1, -6% at 16. It adds 0.94 GiB of weights and leaves 1.88 GiB of KV cache (5.00x concurrency). The answers are the same as the baseline.
- **`compile` equals the baseline.** Out tok/s of `chat` at concurrency 16: 1028.6 against 1047.2. vLLM v0.28.0 uses the same compile mode by default.
- **AWQ is the largest change.** Weights 1.95 GiB (fp16: 5.79 GiB). Out tok/s of `chat`: +134% at concurrency 1, +124% at 16. TPOT p50 of `chat` at concurrency 1: 6.0 ms against 14.2 ms. The KV cache is 6.89 GiB (24.50x concurrency). The quantization changes the answers: 4 of 14 answers differ from the baseline.
- **Scheduler sizing (`sched_085`: `max-num-seqs` 8, `max-model-len` 4096) is not better than the baseline.** Out tok/s of `chat` at concurrency 1 and 8 equal the baseline (68.4 and 528.4 against 70.7 and 539.1). At concurrency 16 the engine can run only 8 requests, so the other 8 wait: TTFT p50 is 1,970 ms (baseline 52 ms) and out tok/s is 528.2 (baseline 1,047.2, -50%). This is the same collapse that the source project saw at concurrency 16 with `max-num-seqs` 8. The answers are the same as the baseline (14 of 14, and the Thai fact set).
- **fp8 KV cache (`kv_fp8_085`) works on the RTX 4070 SUPER and gives 1.76 times more KV cache.** 183,232 tokens against 103,840 for `sched_085`, which has the same scheduler flags (the source project could not run it on a T4). It gives no speed gain here: out tok/s of `chat` is 69.0 / 527.4 / 534.0, the same as `sched_085`, because the batch limit of 8 is the limit and not the KV cache. The cost is quality: 4 of 14 answers differ from the baseline, and in the Thai fact set the answers to the provinces (76 against 64) and the mountain change. Both sets still fail the same two facts. The pass count is the same as the baseline (11 of 14, 2 of 4). A bigger KV cache has no use for one user, so keep `baseline`.
- **No request failed and no preemption happened** in any run. At concurrency 16 with `--max-num-seqs 16`, the engine is at its limit, so the TTFT p99 of `random` includes queue time.
- **Prefix caching:** it is on in every configuration. No configuration turns it off, so its own effect is not measured.
- **Thai facts (extra check):** 4 harder Thai questions in `bench/prompts/quality_prompts_th_fact.json`, run with `--prompts quality_prompts_th_fact.json` at temperature 0. `baseline` and `awq` both pass 2 of 4 (`awq-thfact` and `baseline-thfact` in `bench/results/`). Both fail the number of provinces (`baseline` answers 64, `awq` answers 54, the right number is 77) and the highest mountain (both answer Doi Suthep, the right answer is Doi Inthanon). Both pass the capital of Japan and the formula of water. So this model is weak on Thai facts in fp16 too, and this set does not separate `awq` from `baseline`. The `awq` answer 54 is the same wrong number that the source project found. Do not read the 12/14 against 11/14 of `awq` as a quality gain.
- **Thai quality:** every configuration gives 3 or 4 of 6 Thai prompts. The check is a word test. It is a guard for lossless levers, not a measure of Thai quality.

### Tables of each configuration

#### `ngram_chunked`

| workload | conc | TTFT p50 (ms) | TTFT p99 (ms) | TPOT p50 (ms) | TPOT p99 (ms) | out tok/s | req/s | done | failed |
|---|---|---|---|---|---|---|---|---|---|
| chat | 1 | 21.1 | 23.3 | 15.6 | 16.8 | 65.0 | 0.5 | 24 | 0 |
| chat | 8 | 35.8 | 47.3 | 17.0 | 17.8 | 464.8 | 3.6 | 96 | 0 |
| chat | 16 | 39.0 | 83.0 | 18.4 | 19.9 | 851.9 | 6.7 | 160 | 0 |
| prefix | 1 | 36.9 | 37.6 | 4.8 | 15.9 | 142.7 | 1.1 | 24 | 0 |
| prefix | 8 | 64.9 | 215.0 | 6.8 | 24.7 | 838.6 | 6.6 | 96 | 0 |
| random | 1 | 56.7 | 57.9 | 4.9 | 15.9 | 142.0 | 1.1 | 24 | 0 |
| random | 8 | 80.3 | 122.8 | 7.5 | 25.9 | 756.6 | 5.9 | 96 | 0 |
| random | 16 | 86.3 | 713.3 | 9.5 | 34.2 | 1099.2 | 8.6 | 160 | 0 |

#### `spec_ngram`

| workload | conc | TTFT p50 (ms) | TTFT p99 (ms) | TPOT p50 (ms) | TPOT p99 (ms) | out tok/s | req/s | done | failed |
|---|---|---|---|---|---|---|---|---|---|
| chat | 1 | 21.4 | 23.3 | 15.8 | 16.5 | 64.5 | 0.5 | 24 | 0 |
| chat | 8 | 36.9 | 49.9 | 17.5 | 18.6 | 449.6 | 3.5 | 96 | 0 |
| chat | 16 | 39.8 | 81.0 | 18.8 | 19.6 | 826.2 | 6.5 | 160 | 0 |
| prefix | 1 | 37.3 | 41.6 | 4.9 | 16.3 | 139.4 | 1.1 | 24 | 0 |
| prefix | 8 | 64.9 | 262.2 | 7.3 | 24.5 | 765.7 | 6.0 | 96 | 0 |
| random | 1 | 56.3 | 58.0 | 4.8 | 16.2 | 142.0 | 1.1 | 24 | 0 |
| random | 8 | 80.1 | 123.4 | 6.6 | 25.5 | 799.3 | 6.2 | 96 | 0 |
| random | 16 | 56.3 | 170.3 | 8.2 | 34.9 | 1369.6 | 10.7 | 160 | 0 |

#### `spec_draft`

| workload | conc | TTFT p50 (ms) | TTFT p99 (ms) | TPOT p50 (ms) | TPOT p99 (ms) | out tok/s | req/s | done | failed |
|---|---|---|---|---|---|---|---|---|---|
| chat | 1 | 62.8 | 115.5 | 11.7 | 14.7 | 80.7 | 0.6 | 24 | 0 |
| chat | 8 | 98.9 | 150.1 | 13.4 | 16.2 | 548.6 | 4.3 | 96 | 0 |
| chat | 16 | 106.1 | 148.6 | 14.3 | 18.1 | 987.6 | 7.7 | 160 | 0 |
| prefix | 1 | 84.4 | 85.5 | 8.2 | 11.9 | 110.6 | 0.9 | 24 | 0 |
| prefix | 8 | 155.3 | 303.5 | 10.9 | 24.2 | 594.1 | 4.6 | 96 | 0 |
| random | 1 | 103.6 | 105.5 | 8.2 | 17.4 | 97.5 | 0.8 | 24 | 0 |
| random | 8 | 155.1 | 334.6 | 11.4 | 23.8 | 558.8 | 4.4 | 96 | 0 |
| random | 16 | 203.8 | 983.6 | 14.6 | 40.5 | 820.2 | 6.4 | 160 | 0 |

#### `compile`

| workload | conc | TTFT p50 (ms) | TTFT p99 (ms) | TPOT p50 (ms) | TPOT p99 (ms) | out tok/s | req/s | done | failed |
|---|---|---|---|---|---|---|---|---|---|
| chat | 1 | 22.6 | 23.6 | 14.5 | 14.6 | 68.7 | 0.5 | 24 | 0 |
| chat | 8 | 47.3 | 50.6 | 14.8 | 14.9 | 529.3 | 4.1 | 96 | 0 |
| chat | 16 | 49.5 | 81.0 | 15.2 | 15.3 | 1028.6 | 8.0 | 160 | 0 |
| prefix | 1 | 37.6 | 47.9 | 14.5 | 14.8 | 68.0 | 0.5 | 24 | 0 |
| prefix | 8 | 169.2 | 215.8 | 15.6 | 16.5 | 476.3 | 3.7 | 96 | 0 |
| random | 1 | 57.1 | 61.6 | 14.4 | 14.4 | 68.5 | 0.5 | 24 | 0 |
| random | 8 | 218.3 | 388.8 | 15.4 | 17.6 | 461.4 | 3.6 | 96 | 0 |
| random | 16 | 79.8 | 613.7 | 15.8 | 20.7 | 879.0 | 6.9 | 160 | 0 |

#### `awq`

| workload | conc | TTFT p50 (ms) | TTFT p99 (ms) | TPOT p50 (ms) | TPOT p99 (ms) | out tok/s | req/s | done | failed |
|---|---|---|---|---|---|---|---|---|---|
| chat | 1 | 13.2 | 20.0 | 6.0 | 6.0 | 165.2 | 1.3 | 24 | 0 |
| chat | 8 | 26.9 | 36.3 | 6.2 | 6.3 | 1256.2 | 9.8 | 96 | 0 |
| chat | 16 | 42.1 | 53.5 | 6.5 | 6.7 | 2345.5 | 18.3 | 160 | 0 |
| prefix | 1 | 36.4 | 37.9 | 5.9 | 6.0 | 161.5 | 1.3 | 24 | 0 |
| prefix | 8 | 196.6 | 211.9 | 6.6 | 7.8 | 992.0 | 7.7 | 96 | 0 |
| random | 1 | 56.1 | 56.8 | 5.9 | 6.0 | 158.6 | 1.2 | 24 | 0 |
| random | 8 | 189.5 | 287.4 | 7.1 | 8.8 | 930.0 | 7.3 | 96 | 0 |
| random | 16 | 66.5 | 519.4 | 7.2 | 12.4 | 1666.9 | 13.0 | 160 | 0 |

#### `sched_085`

| workload | conc | TTFT p50 (ms) | TTFT p99 (ms) | TPOT p50 (ms) | TPOT p99 (ms) | out tok/s | req/s | done | failed |
|---|---|---|---|---|---|---|---|---|---|
| chat | 1 | 23.6 | 40.0 | 14.6 | 14.8 | 68.4 | 0.5 | 24 | 0 |
| chat | 8 | 47.5 | 54.5 | 14.8 | 15.8 | 528.4 | 4.1 | 96 | 0 |
| chat | 16 | 1969.6 | 2017.8 | 15.0 | 15.1 | 528.2 | 4.1 | 160 | 0 |
| prefix | 1 | 38.0 | 55.0 | 14.6 | 15.2 | 67.7 | 0.5 | 24 | 0 |
| prefix | 8 | 171.4 | 226.4 | 15.4 | 16.5 | 477.6 | 3.7 | 96 | 0 |
| random | 1 | 58.1 | 61.3 | 14.4 | 15.4 | 67.3 | 0.5 | 24 | 0 |
| random | 8 | 213.0 | 349.2 | 15.1 | 17.2 | 468.2 | 3.7 | 96 | 0 |
| random | 16 | 2559.6 | 2806.0 | 16.0 | 18.1 | 443.7 | 3.5 | 160 | 0 |

#### `kv_fp8_085`

| workload | conc | TTFT p50 (ms) | TTFT p99 (ms) | TPOT p50 (ms) | TPOT p99 (ms) | out tok/s | req/s | done | failed |
|---|---|---|---|---|---|---|---|---|---|
| chat | 1 | 25.5 | 30.1 | 14.4 | 14.6 | 69.0 | 0.5 | 24 | 0 |
| chat | 8 | 62.8 | 77.3 | 14.8 | 15.2 | 527.4 | 4.1 | 96 | 0 |
| chat | 16 | 1949.3 | 1963.4 | 14.8 | 14.9 | 534.0 | 4.2 | 160 | 0 |
| prefix | 1 | 38.4 | 71.7 | 14.3 | 14.6 | 68.7 | 0.5 | 24 | 0 |
| prefix | 8 | 175.0 | 214.2 | 15.2 | 16.3 | 483.8 | 3.8 | 96 | 0 |
| random | 1 | 63.4 | 69.2 | 14.4 | 14.6 | 67.5 | 0.5 | 24 | 0 |
| random | 8 | 213.2 | 387.5 | 15.3 | 17.4 | 464.7 | 3.6 | 96 | 0 |
| random | 16 | 1991.4 | 2628.1 | 14.9 | 17.3 | 497.1 | 3.9 | 160 | 0 |

Preemptions (not checked for `sched_085` and `kv_fp8_085`, no request failed in them): `baseline` 0, `ngram_chunked` 0, `spec_ngram` 0, `spec_draft` 0, `compile` 0, `awq` 0. No request failed in any run.

### Multi-turn chat (workload `multiturn`)

Added after the final choice, to test a case that the `chat` workload does not cover: a prompt with
earlier turns in it. The file is `bench/prompts/multiturn_prompts.jsonl` (8 conversations, 82 to 129 words
each, in English). The turns go into one user message as a transcript, and some last questions ask the
model to rewrite or summarize what it said before. Run with `WORKLOADS=multiturn bench/run.sh <label>`.
`baseline` and `spec_ngram` are measured (the Deployment was set to `spec_ngram` for the run and
set back to `baseline` after it).

| config | conc | TTFT p50 (ms) | TPOT p50 (ms) | out tok/s | done | failed |
|---|---|---|---|---|---|---|
| `baseline` | 1 | 21.7 | 14.5 | 68.7 | 24 | 0 |
| `spec_ngram` | 1 | 21.5 | 15.3 | 69.8 | 24 | 0 |
| `baseline` | 8 | 47.1 | 14.8 | 530.7 | 96 | 0 |
| `spec_ngram` | 8 | 38.2 | 17.2 | 458.1 | 96 | 0 |
| `baseline` | 16 | 62.4 | 15.3 | 1018.5 | 160 | 0 |
| `spec_ngram` | 16 | 41.0 | 18.7 | 839.3 | 160 | 0 |

What the numbers show:
- `baseline` on this workload is close to `baseline` on `chat` (68.7, 529.3, and 1028.6 out tok/s).
  The history is short, so it adds little prefill work.
- N-gram decoding does not win here. At concurrency 1 the out tok/s is the same (+1.6%) and the TPOT p50
  is 0.8 ms worse. At concurrency 8 and 16 the out tok/s is -14% and -18%, and the TPOT p50 is worse.
- The TTFT of `spec_ngram` is lower at concurrency 8 and 16. This is not explained. Do not read it as a gain.
- The accept rate of the guessed tokens is not read, so the run does not show how often n-gram guessed right.
- `vllm bench serve` does not send `temperature=0` in this version, so the server default sampling
  applies. This can lower the accept rate. It is not tested with `--temperature=0`.
- Each run is one run. The prompts are 82 to 129 words, so the history is short.

### Summarize a text (workload `summarize`)

The case that n-gram decoding is made for: the answer copies words of the prompt. The file is
`bench/prompts/summarize_prompts.jsonl` (5 prompts, each "Summarize the following text in five short
bullet points" and a text of 411 to 460 words, cut from `docs/GUIDE.md` and `CLAUDE.md`). The run uses
`--temperature 0`. Run with `WORKLOADS=summarize bench/run.sh <label>`. Each configuration ran once.

| config | conc | TTFT p50 (ms) | TPOT p50 (ms) | out tok/s | done | failed |
|---|---|---|---|---|---|---|
| `baseline` | 1 | 23.1 | 14.4 | 68.7 | 24 | 0 |
| `spec_ngram` | 1 | 23.0 | 12.6 | 79.0 | 24 | 0 |
| `baseline` | 8 | 50.2 | 14.9 | 523.9 | 96 | 0 |
| `spec_ngram` | 8 | 40.9 | 15.7 | 495.3 | 96 | 0 |
| `baseline` | 16 | 55.1 | 15.5 | 1003.7 | 160 | 0 |
| `spec_ngram` | 16 | 46.4 | 17.8 | 861.0 | 160 | 0 |

- At concurrency 1, n-gram helps: out tok/s +15%, TPOT p50 -12%.
- At concurrency 8 and 16, n-gram costs: out tok/s -5% and -14%.
- So the gain of n-gram is real but small, and only for one request at a time. The cost grows with the load.
- The accept rate is not read, so the cause is not measured.

Final choice: `baseline` (fp16, utilization 0.85, max-model-len 8192, max-num-seqs 16, prefix caching), with `VLLM_USE_V2_MODEL_RUNNER=0` on WSL2. The Deployment and the configuration `deployed` use it.

Reasons:
- It is the fastest lossless configuration for the chat workload. Out tok/s of `chat` at concurrency 16: 1047.2, against 851.9 for `ngram_chunked` (the earlier Deployment).
- N-gram decoding helps `random` and costs 9% to 21% of `chat` throughput. The product is a chat.
- Its answers are the reference for the quality check (14 of 14 for every lossless configuration).
- Utilization 0.85 starts on this PC. 0.92 does not.

Limits of this choice:
- The reasons use the numbers at concurrency 16. This project has one user, which is closer to concurrency 1. At concurrency 1, `spec_draft` is +14% and `awq` is +134% faster than `baseline`, and n-gram is 9% slower. The choice of `baseline` stands because it is the simplest and the reference, not because it is the fastest at concurrency 1.
- The `chat` workload is 28 short single-turn prompts with `--ignore-eos`, and each configuration ran once. The spread between runs is not measured. The multi-turn case (see above) gives no gain for n-gram. The summarize case (see above) gives +15% at concurrency 1 and a loss at higher load.
- It is not known how much of the n-gram cost comes from wrong guesses and how much from the async scheduling that vLLM turns off with n-gram.
- For one user at a time, n-gram is -9% for `chat`, +1.6% for `multiturn`, and +15% for `summarize`. Choose it only if the product mostly summarizes or quotes text. The chatbot of this project mostly chats.
- That the source project gets a gain from n-gram because it runs on a T4 is a guess. It is not tested.

AWQ is the largest gain (+124% out tok/s of `chat` at concurrency 16), but 4 of 14 answers differ. It stays an option for multi-instance (see `CLAUDE.md`). `sched`, `kv_fp8`, and `min_latency` are not measured (they need utilization 0.92).

## Several AWQ pods on one GPU (router spec, ticket 01)

Measured on WSL2 on 2026-11-14 with `k8s/vllm-awq-pool.yaml` (Qwen2.5-3B-Instruct-AWQ, max-model-len
8192, max-num-seqs 16, prefix caching). The fp16 pod was at zero replicas. Each pod started after the
one before it was ready. The log is in `bench/results/pool-vram/` (not in git).

**Finding before the numbers:** the second pod stayed `Pending` with `Insufficient nvidia.com/gpu`. The
node had one `nvidia.com/gpu`, and the first pod held it, although the VRAM was free. The fix is
time-slicing in the NVIDIA device plugin (`replicas: 3` in `k8s/nvidia-device-plugin.yaml`). The node
then reports `nvidia.com/gpu: 3`. Time-slicing does not split the VRAM. Each pod keeps its own
`--gpu-memory-utilization`.

| Pods | Utilization of each | Weights each (GiB) | KV cache each (GiB, tokens, concurrency at 8192) | GPU used after the pods (MiB, with 860 MiB of desktop) | Result |
|---|---|---|---|---|---|
| 1 (`a`) | 0.40 | 1.95 | 2.29, 72,832, 8.89x | 5837 | ready |
| 2 (`a`, `b`) | 0.40 | 1.95 | 2.23 to 2.29, 72,832, 8.89x | 10851 | both ready and both answered a chat request |
| 1 (`a`) | 0.29 | 1.95 | 0.97, 34,416, 4.20x | 4479 | ready |
| 2 (`a`, `b`) | 0.29 | 1.95 | 0.97, 34,416, 4.20x | 8105 | both ready |
| 3 (`a`, `b`, `c`) | 0.29 | 1.95 | not started | 8094 | `c` stopped: `ValueError: No available memory for the cache blocks` |

- **Two pods fit.** Each pod at 0.40 uses about 5 GiB (5837 MiB for the first, 5014 MiB more for the
  second). The total of 10851 MiB leaves about 1.4 GiB of the 12,282 MiB.
- **A third pod does not start at 0.29.** The cause is not analyzed. Other shares were not tested, so
  this does not prove that three pods never fit. The router plan uses two pods.
- The pods have the same KV cache size, so the router can compare them only by load and by prefix.
- vLLM prints a line that tells a `--kv-cache-memory` value for a start without a profile. It was not
  used.

## Voice (ticket 06)

Measured on 2026-11-13 on WSL2 with `bench/voice_latency.py` (inside the vLLM pod, with the final
flags, STT `small.en` on CPU, TTS Piper on CPU). It follows the voice mode: STT, then the LLM answer
until the end of its first sentence, then TTS of that sentence. 4 short English questions, 5 runs each
after a warm-up. There is no microphone in the test, so the time to detect the end of speech is not in the numbers.

| Step | p50 (s) | max (s) |
|---|---|---|
| STT | 1.08 | 1.19 |
| LLM, first token | 0.05 | 0.32 |
| LLM, first sentence | 0.25 | 0.81 |
| TTS of the first sentence | 1.57 | 3.83 |
| Total, end of speech to first audio | 2.85 | 5.76 |

The GPU part (the LLM) is about 0.25 s of 2.85 s. The two CPU steps are the cost: STT 1.08 s and TTS
1.57 s. The TTS server returns the whole file, so a long first sentence makes the wait longer (max 3.83 s). The
real wait in the browser is longer, because it adds the pause that detects the end of speech. This
is not measured. The microphone worked in the browser on 2026-11-14 (the STT pod returned HTTP 200 for the speech). Not tested: the voice call, and the overlap between sentences.

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

