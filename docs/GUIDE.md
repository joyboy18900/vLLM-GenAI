# Guide: how a request moves through the system

This guide explains what happens from the moment you send a message to the moment you get an
answer. It also explains what k3s does at each step and how to read the dashboards.

Read it once from the top. Then use it as a map when something does not work.

**Status of this guide:** it describes the design of the system. Part of the system ran on the
local PC in WSL2 and the rest is not tested yet (see `docs/setup.md` and the README). Where a number
depends on a measurement, the guide says so and does not give a number.

## Part 0: the parts of the system

| Part | What it does | Service name and port |
|---|---|---|
| Open WebUI | The chat page. It takes your text or voice and calls the other parts. | `webui` 8080 |
| vLLM | Runs the chat model (Qwen3.5-4B) on the GPU. | `vllm` 8000 |
| STT (faster-whisper) | Turns speech into text. Runs on the CPU. | `stt` 8000 |
| TTS (Piper) | Turns text into speech. Runs on the CPU. | `tts` 8000 |
| k3s | Runs all the parts as pods and connects them. | - |
| Traefik | The entry door of k3s. It gives HTTPS host names. | ports 80 and 443 |
| Prometheus | Collects numbers (metrics) from the parts every 10 seconds. | `prometheus` 9090 |
| Grafana | Shows the numbers and the logs. | `grafana` 3000 |
| DCGM exporter | Reads GPU temperature, load, memory, and power. | `dcgm-exporter` 9400 |
| Node Exporter | Reads CPU, RAM, and disk of the machine. | port 9100 |
| kube-state-metrics | Reads the state of pods and Deployments. | `kube-state-metrics` 8080 |
| Loki and Alloy | Alloy reads the logs of all pods. Loki stores them. | `loki` 3100 |
| Alertmanager | Receives alerts from Prometheus. | `alertmanager` 9093 |

The speech parts and the monitoring parts do not use the GPU. Only vLLM uses it.

## Part 1: you type a message

### 1.1 From the browser to the chat page

You open the page in one of two ways:

- **HTTPS.** The browser calls `https://webui.genai.test`. The name points to the machine. Traefik
  receives the call on port 443, reads the host name, and sends it to the Service `webui`.
- **SSH tunnel.** The browser calls `http://localhost:8080`. The tunnel carries the call to port
  30080 on the machine. That is the NodePort of the Service `webui-nodeport`.

Both ways end at the same Open WebUI pod.

### 1.2 From the chat page to the model

Open WebUI does not run the model. It sends an HTTP call to the Service `vllm`. The format is the
OpenAI chat API. This is the call, in short:

```
POST http://vllm:8000/v1/chat/completions
{
  "model": "Qwen/Qwen3.5-4B",
  "messages": [ {"role": "user", "content": "Say hi"} ],
  "stream": true
}
```

The name `vllm` works because k3s has a small DNS service. It turns the name of a Service into the
address of the pod behind it.

### 1.3 What happens inside vLLM

1. **Tokenize.** vLLM cuts your text into tokens (small pieces of words).
2. **Prefill.** vLLM reads all the input tokens at once and fills the KV cache. The KV cache holds
   the attention data of the tokens that vLLM already read. The time until the first token comes
   back is the TTFT.
3. **Decode.** vLLM makes one token, adds it to the KV cache, and repeats. The time for each token
   is the TPOT.
4. **Batching.** vLLM can serve many requests at the same time. It adds new requests to the batch
   at every step (continuous batching). `--max-num-seqs` sets the maximum.
5. **Memory.** vLLM cuts the KV cache into blocks (PagedAttention). If the cache is full, vLLM
   waits or preempts a request. A preempted request loses its blocks and is computed again. The
   dashboard shows this.

Thinking mode is off. The server flag `--default-chat-template-kwargs` sets `enable_thinking` to
false. The model answers at once, which keeps voice answers fast.

### 1.4 The answer comes back in pieces

`"stream": true` makes vLLM send each token as soon as it exists. The format is Server-Sent Events:
lines that start with `data:`. Open WebUI passes them to the browser, and you see the answer grow
word by word.

## Part 2: you speak

Voice mode has three steps. Open WebUI runs all three.

### 2.1 Speech to text

The browser records your voice. Open WebUI sends the audio to the Service `stt`:

```
POST http://stt:8000/v1/audio/transcriptions   (the audio file in a form)
-> {"text": "..."}
```

The STT pod runs faster-whisper with the model `small.en` on the CPU (int8). It uses greedy
decoding, a fixed language, and a voice activity filter. These choices make it fast and stop it
from guessing a wrong language.

### 2.2 Think

The text goes to vLLM. This is the same path as in Part 1.

### 2.3 Text to speech

Open WebUI does not wait for the full answer. It cuts the stream at punctuation
(`AUDIO_TTS_SPLIT_ON=punctuation`). For each sentence it calls the Service `tts`:

```
POST http://tts:8000/v1/audio/speech   {"input": "Hello there."}
-> a WAV file
```

The TTS pod starts Piper for each call and returns the sound. Two settings keep the sentences
clean. The pod makes one sound at a time, so sentences do not overlap. It adds no silence after a
sentence, so there is no gap. The first sentence plays while the model still writes the rest.

### 2.4 Why the microphone needs HTTPS or localhost

A browser gives the microphone only to a secure page. A page is secure when it uses HTTPS or when
its address is `localhost`. An SSH tunnel makes the address `localhost`. Plain HTTP to another
address does not work.

### 2.5 What makes the voice answer slow or fast

The time from the end of your speech to the first sound is the sum of four parts: the STT time,
the TTFT of vLLM, the time to write the first sentence, and the TTS time for that sentence. The
benchmarks document records the measured value after the first test.

## Part 3: what k3s does

k3s is a small Kubernetes. It runs on one machine here.

### 3.1 Names and load sharing

Every Service has a stable name and a stable address. If a pod restarts and gets a new address, the
name still works. If a Service has more than one ready pod, k3s shares the calls between them.
Here, each Service has one pod.

### 3.2 The door to the outside

A NodePort opens a port on the machine (30080 for the web UI, 30300 for Grafana). Traefik, the
default k3s Ingress controller, adds HTTPS and host names. A local certificate authority makes the
certificate. No key is in the repository.

### 3.3 Giving the GPU to a pod

The NVIDIA device plugin tells k3s that the machine has one GPU (`nvidia.com/gpu: 1`). A pod that
asks for one GPU gets it. The `nvidia` RuntimeClass makes the container runtime show the GPU to the
pod. The DCGM exporter uses the runtime class too, but it does not ask for the GPU. It only reads
data, so it does not take the GPU from vLLM.

### 3.4 The Recreate rule

There is one GPU. When vLLM updates, k3s must stop the old pod before it starts the new one. This
is the `Recreate` strategy. A normal rolling update would start the new pod first and wait for a
second GPU that does not exist. Open WebUI, Prometheus, Grafana, and Loki use `Recreate` too,
because their data volume can be used by one pod at a time.

### 3.5 Health checks

Each pod has three checks on `/health` (or a similar route):

- **Startup.** It gives a slow start, such as a first model download, up to 15 minutes. The other
  checks wait until it passes.
- **Readiness.** If it fails, k3s removes the pod from the Service. No calls reach a pod that is
  not ready.
- **Liveness.** If it fails three times, k3s restarts the pod.

### 3.6 Data that must stay

A PersistentVolumeClaim (PVC) is a disk that stays when a pod restarts. This system uses PVCs for
the model files, the compile caches, the voices, the chat history, and the data of Prometheus,
Grafana, and Loki. A restart of vLLM does not download the model again. The storage class is
`local-path`, which uses a folder on the machine.

### 3.7 No automatic environment variables

By default, k3s adds environment variables for every Service into every pod. The Service `vllm`
makes a variable named `VLLM_PORT`. vLLM reads a variable with the same name for its own use, and it
crashes. Each pod here sets `enableServiceLinks: false` to stop this.

### 3.8 The helper that runs first

The TTS pod has an init container. It runs before the main container and downloads the voice file
into the PVC if the file is not there. The main container starts after the init container ends.

## Part 4: all paths in one picture

```
Browser
  |  HTTPS (Traefik :443)  or  SSH tunnel (NodePort :30080)
  v
Open WebUI  (webui:8080)
  |-- typed text ----------------------------------> vLLM (vllm:8000) --> GPU
  |-- voice: audio -> STT (stt:8000) -> text --------^        |
  |-- answer text, sentence by sentence -> TTS (tts:8000) -> sound
  v
Browser (text appears, sound plays)

Prometheus <-- vLLM, STT, TTS, DCGM, Node Exporter, kube-state-metrics, itself
Alloy      --> Loki   (logs of all pods)
Grafana    --> reads Prometheus and Loki
Alertmanager <-- alerts from Prometheus rules
```

## Part 5: what is not built yet

The design in `CLAUDE.md` has more than the system has today. These parts are planned, as in the
reference project, and are not built:

- the mock LLM-D router and scale-to-zero
- the feedback collector with Redis Streams
- the weekly retraining CronJob (LoRA and DPO) and the hot swap of the adapter

The Thai voice is a bonus for later.

## Part 6: how to open the pages

| Page | HTTPS address | SSH tunnel |
|---|---|---|
| Open WebUI | `https://webui.genai.test` | `-L 8080:localhost:30080`, then `http://localhost:8080` |
| Grafana | `https://grafana.genai.test` | `-L 3000:localhost:30300`, then `http://localhost:3000` |
| Prometheus | - | `kubectl -n monitoring port-forward svc/prometheus 9090:9090` |
| Alertmanager | - | `kubectl -n monitoring port-forward svc/alertmanager 9093:9093` |

Common problems:

- **The microphone is blocked.** You use plain HTTP on an address that is not `localhost`. Use the
  tunnel or HTTPS.
- **The tunnel says the port is in use.** Another tunnel or program uses the local port. Close it or
  choose another local port.
- **The browser warns about the certificate.** The Mac does not trust the local certificate
  authority yet. See the HTTPS section in `docs/setup.md`.
- **The page does not load after a restart.** vLLM needs time to start. Run
  `kubectl get pods` and wait until the pod is `Ready`.

## Part 7: how to read the dashboard

Open Grafana and then the dashboard "vLLM Serving - SLO, KV cache, GPU". Send a few chat messages
first, because the panels are empty without traffic. The data source is Prometheus. Each row answers
one question.

### Row 1: SLO (does the user feel it is fast?)

- **TTFT.** The wait before the first word. High values mean a long prompt or a queue.
- **TPOT.** The time for each word after the first. High values mean the GPU is busy.
- **E2E latency.** The total time of a request.
- **Throughput.** Tokens per second, for the input and the output.
- **Finish reasons.** `stop` is normal. `length` means the answer hit the limit. `abort` means the
  client left.
- **Queue time.** The wait before the engine starts a request.

### Row 2: saturation (is the machine full?)

- **KV cache usage.** Near the maximum means requests wait or get preempted.
- **Running and waiting requests.** Many waiting requests mean the batch limit is too low or the load
  is too high.
- **Preemptions.** Should stay at zero. If not, lower `--max-num-seqs` or `--max-model-len`.
- **Prefix cache hit rate.** High values mean vLLM reuses shared prompt parts.
- **Batch size.** The number of tokens per step.
- **Speculative decoding acceptance.** Empty when the feature is off.

### Row 3: GPU

Temperature, load, power, VRAM, and clocks, from the DCGM exporter. The desktop display also uses
VRAM on the local PC.

### Row 4: node and pods

CPU, RAM, and disk of the machine, the phase of each pod, and the restarts in the last hour. A
rising restart count shows a crash loop.

### Row 5: speech

The request rate and the latency of STT and TTS. A round trip of text to speech to text moves these
panels.

### Logs and alerts

- **Logs.** In Grafana, open Explore, choose Loki, and search, for example `{app="vllm"}`. The
  label `app` also has the values `stt`, `tts`, and `open-webui`.
- **Alerts.** Prometheus checks four rules: a target is down, vLLM preempted requests, the GPU is
  hotter than 85 C, and the KV cache is above 90 percent. Alertmanager lists the active alerts. It
  has no email or chat channel, so you read them on its page.
