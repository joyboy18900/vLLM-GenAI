# CLAUDE.md

Guidance for Claude Code when it works in this project.

## Project Overview

A practice project for **LLM serving infrastructure**, end to end. The product is a voice chatbot (type or speak, a ChatGPT-like UI with voice mode). Open WebUI is the frontend. It connects to a backend that simulates the architecture of a production-grade inference platform, with a **continual learning loop** from user feedback.

**Learning goals.** The goal is not only a chatbot. The goal is to practice:
- vLLM: workload tuning, KV cache (vLLM manages all of it), GPU memory optimization, quantization (AWQ), LoRA serving
- Kubernetes: pod scheduling, load balancing, **CronJob for scheduled retraining**
- LLM-D concept: simulate the choice of the best GPU or instance for each request
- **Streaming data pipeline + preference-based fine-tuning** (DPO) from real user feedback

## Hardware

| Part | Spec |
|---|---|
| Environment | Local PC, Ubuntu (bare metal) |
| CPU | AMD Ryzen 7 8700F, 8 cores / 16 threads |
| RAM | 32GB DDR5 |
| GPU | 1x NVIDIA **RTX 4070 SUPER**, VRAM 12GB (Ada, no NVFP4) |

The CPU has no integrated graphics. The desktop display also uses the RTX 4070 SUPER, so some VRAM is not available to vLLM.

**Approximate VRAM budget** (everything on one 12GB RTX 4070 SUPER):

| Part | VRAM |
|---|---|
| Qwen3.5-4B (bf16) | ~8GB |
| KV cache + batching headroom | ~2-3GB |
| Desktop display | ~0.5-1GB |
| faster-whisper (STT) | 0 (CPU only, no GPU) |
| Piper (TTS) | 0 (CPU only, no GPU) |

**Main constraint**: there is one GPU only. Serving and retraining must share the same GPU. The retraining job (Sunday 02:00) must scale down the serving pod while it trains (see Key Design Decision 6).

**If you run on EC2.** The PC is the main machine, but the same stack can run on an EC2 GPU instance. Check these differences first:
- An older GPU (before Ada) can have no fp8 and no bf16. Then use fp16.
- The VRAM size is different. Calculate the VRAM budget and `--gpu-memory-utilization` again.
- No desktop display uses the GPU, so more VRAM is available.
- A new AWS account must request a GPU instance quota before the first launch.
- You pay for each hour. Stop the instance when you do not use it.
- Open the web UI from another computer through an SSH tunnel or HTTPS. The browser blocks the microphone on plain HTTP.

## Models (2)

1. **Qwen3.5-4B** (chat): [HuggingFace](https://huggingface.co/Qwen/Qwen3.5-4B), bf16, served by vLLM, supports LoRA adapters for weekly retraining. Thinking mode is off by default, because it makes voice replies slow.
2. **Speech stack** (the "speak" side)
   - **STT**: faster-whisper (small/base model), fast and light
   - **TTS**: Piper, CPU only, low latency, takes no VRAM from the LLM

> For better voice quality in the future, consider Kokoro or XTTS-v2 instead of Piper, but plan for more VRAM (~1.5GB+).
> Voice mode is English first. A Thai TTS voice is a later bonus.

## Architecture (Data Plane)

```
User (text or voice) → Open WebUI
  → [voice] STT (faster-whisper) converts speech to text first
  → LLM-D router (mock) → vLLM pod (Qwen3.5-4B) → response
  → [voice mode] TTS (Piper) converts the text back to speech
  → back to the user
```

The k8s Service does basic load balancing (round-robin across ready pods). The LLM-D router is a smarter layer (it chooses by KV cache hit rate and queue depth). STT and TTS are separate pods. They do not go through the LLM-D router, because they are a different workload (they need no GPU choice, because they are very light and can stay always-on).

## Key Design Decisions

### 1. Mock LLM-D instead of real multi-GPU
There is one GPU only (RTX 4070 SUPER), so multi-instance is simulated with more than one pod definition in k8s.

### 2. Scale-to-zero for idle chat pods
A pod with no users goes to replica = 0 and uses no VRAM. When a request comes in, the pod does a cold start.

### 3. AWQ/GPTQ (INT4) instead of NVFP4
The RTX 4070 SUPER (Ada) has no FP4 Tensor Cores. Use AWQ/GPTQ for real quantization. Ada also supports fp8 weights and fp8 KV cache.

### 4. k3s on one machine
Single-node cluster on the Ubuntu PC, with NVIDIA Container Toolkit + nvidia-device-plugin.

### 5. STT and TTS as separate pods, always-on
They are very light (Piper uses no GPU, faster-whisper runs on CPU). They do not need scale-to-zero like the LLM pod.

### 6. Retraining shares the GPU with serving, so scale down for a short time
There is one GPU only. When the CronJob runs training, it must scale the vLLM chat pod replicas down for a short time (Sunday 02:00 is a low-traffic window for a single user). After training, scale back up with the new adapter.

### 7. LoRA + DPO instead of full fine-tune
12GB of VRAM is not enough for a full fine-tune of a 4B model (the optimizer state is too large). Use **LoRA** (PEFT) with **DPO** (TRL) instead. It is much lighter, and vLLM can load a LoRA adapter dynamically without a full pod restart.

### 8. Feedback as preference pairs for DPO
👍 = chosen, 👎 = rejected, compared for the same prompt. If there are not enough matching pairs, fall back to SFT filtering with only the 👍 responses.

## Continual Learning / Feedback Pipeline

```
Open WebUI (👍/👎 per message)
  → Feedback collector API (FastAPI)
  → Redis Stream (collects feedback events during the week, as a stream)
  → [every Sunday 02:00] k8s CronJob (schedule: "0 2 * * 0")
      → read all Redis Stream data for the week
      → build preference pairs (chosen/rejected)
      → scale down the vLLM chat pod for a short time
      → LoRA + DPO fine-tune (PEFT + TRL)
      → eval on a small held-out set (to prevent regression)
      → if eval passes: hot-swap the LoRA adapter into vLLM, scale back up
      → if eval fails: keep the log, do not deploy, keep the old adapter
```

**Guard condition**: if the feedback data for the week is too small (for example < N samples), the CronJob skips training for that week. Do not train on too little data, because it can make the model worse.

## Tech Stack

- **Serving**: vLLM (internal KV cache, dynamic LoRA loading)
- **Quantization**: AWQ/GPTQ (no NVFP4)
- **Orchestration**: k3s single-node on the Ubuntu PC, with a **CronJob** for weekly retraining
- **GPU scheduling**: NVIDIA Container Toolkit + nvidia-device-plugin
- **Router (LLM-D mock)**: FastAPI + `kubernetes` Python client
- **Frontend**: Open WebUI (Audio settings point to the STT/TTS endpoints)
- **Ingress**: k3s Ingress (Traefik) with HTTPS (TLS)
- **STT**: faster-whisper
- **TTS**: Piper
- **Monitoring and observability**: Prometheus, Grafana, Loki, Alertmanager, DCGM exporter, Node Exporter, kube-state-metrics, `/metrics` on vLLM, STT, and TTS
- **Storage**: PersistentVolumeClaims (models, cache, logs)
- **Feedback streaming**: Redis Streams
- **Training**: PEFT (LoRA) + TRL (DPOTrainer)
- **Chat model**: Qwen3.5-4B (bf16 baseline, AWQ for multi-instance)

## Repo Layout (suggested)

```
.
├── router/                    # FastAPI mock LLM-D router
│   ├── main.py
│   └── k8s_client.py
├── vllm/
│   └── Dockerfile             # supports LoRA adapter mount
├── speech/
│   ├── stt/                   # faster-whisper server
│   └── tts/                   # Piper server
├── feedback/
│   ├── collector.py           # FastAPI, receives 👍/👎 from Open WebUI → Redis Stream
│   └── redis-deployment.yaml
├── training/
│   ├── prepare_pairs.py       # reads the Redis Stream → preference pairs
│   ├── train_dpo_lora.py      # LoRA + DPO fine-tune
│   └── eval.py                # held-out eval before deploy
├── k8s/
│   ├── vllm-deployment.yaml
│   ├── vllm-service.yaml
│   ├── router-deployment.yaml
│   ├── speech-deployment.yaml
│   ├── retrain-cronjob.yaml    # schedule: "0 2 * * 0"
│   ├── nvidia-device-plugin.yaml
│   ├── ingress/               # Ingress + TLS
│   └── monitoring/            # Prometheus, Grafana, Loki, Alertmanager, exporters
├── bench/                     # benchmark harness
└── docs/
    └── benchmarks.md
```

## Development Workflow

1. Run vLLM alone on the PC, tune the flags, test AWQ
2. Deploy as a k3s Deployment + Service
3. Add the router (FastAPI) + scale-to-zero logic
4. Add STT (faster-whisper) + TTS (Piper) as separate pods, connect them to the Open WebUI Audio settings
5. Add the feedback collector + Redis Stream to collect 👍/👎
6. Write the CronJob (`0 2 * * 0`) + training script (LoRA + DPO)
7. Test the hot-swap of a LoRA adapter into vLLM without a full pod downtime
8. Measure everything and record it in `docs/benchmarks.md`

## Next Steps / Roadmap

- [ ] Proof of concept for the full flow (steps 1-8 above)
- [ ] Test real k8s load balancing with 2-3 real AWQ instances at the same time
- [ ] Add a larger eval set for the regression check before each weekly LoRA deploy
- [ ] If a Blackwell machine is available in the future, try NVFP4
- [ ] Thai TTS voice
- [ ] Deploy on EC2

## Notes for Claude Code

- This project is for practice of infra and scheduling. It is not a production system.
- Do not use NVFP4 on this machine (the RTX 4070 SUPER does not support it). Always use AWQ/GPTQ instead. If you run on an EC2 GPU, check that it supports fp8 before you use fp8.
- There is only 1 real GPU. Serving and training must share it. Do not design them to run at full capacity at the same time without scaling one of them down first.
- Retraining uses LoRA only. No full fine-tune (not enough VRAM).
- Before you deploy a new LoRA adapter, always run the eval step first. Do not deploy without a regression check.

## Agent skills

### Issue tracker

Issues and specs are local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary, recorded as a `Status:` line in each issue file. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
