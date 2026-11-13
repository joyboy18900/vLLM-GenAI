# Setup runbook

This runbook sets up the whole system on one machine, in order. Each section has the steps and
a check command with the expected result.

**Test status:** partly tested. Each section starts with its own status. The GPU node, vLLM
standalone, the speech pods, and the Open WebUI pod ran on the local PC in WSL2 (not on bare-metal
Ubuntu or EC2). Parts that ran on a Mac are named in their section (the STT and TTS servers, the
metrics routes, the certificate commands, and the scripts that run on the Mac). Everything else is
written and not tested. After the full run on Ubuntu or EC2, replace this paragraph with the
result and fill the PC spec table in the first section.

Order: PC as a GPU node, vLLM standalone, speech servers, vLLM on k3s, Open WebUI, voice mode,
monitoring, logs, alerts, HTTPS, benchmarks, levers, smoke test. Then "If you run on EC2".

## PC as a GPU node

Status: ran on WSL2 on 2026-11-08 (see "Observed on WSL2" in the WSL2 section). For the run on
bare-metal Ubuntu, install Ubuntu on the PC first. The PC runs Windows now. The commands that need
`sudo` run on the PC (on WSL2 they ran as root with `wsl -u root`).

### PC spec

Fill this table on the PC. Run the command in the second column.

| Item | Command | Value |
|---|---|---|
| CPU | `lscpu \| grep "Model name"` | AMD Ryzen 7 8700F, 8 cores and 16 threads (from the owner, not read by the command) |
| RAM | `free -h` | 32 GB (from the owner). WSL2 limit 24 GB (`free -h` shows 23 GiB). |
| GPU and VRAM | `nvidia-smi --query-gpu=name,memory.total --format=csv` | NVIDIA GeForce RTX 4070 SUPER, 12,282 MiB |
| Disk | `lsblk -o NAME,SIZE,MOUNTPOINT` | Windows drives: C: 465 GB (331 GB free), D: 466 GB (the WSL2 disk is here), E: 466 GB (178 GB free) |
| OS | `lsb_release -d` | Windows (build 10.0.26300) with WSL2 Ubuntu 24.04.5 LTS, kernel 6.18.54.1-microsoft-standard-WSL2 |
| Driver version | `nvidia-smi --query-gpu=driver_version --format=csv,noheader` | Windows driver 616.64. `nvidia-smi` in WSL2 shows 615.65.07 and CUDA 13.4. |

These values come from the run on WSL2 (2026-11-08). Fill them again for the run on bare-metal
Ubuntu and for EC2.

### 1. NVIDIA driver

The desktop display uses this GPU, so install the normal driver (not the headless server one).

```bash
sudo ubuntu-drivers devices      # shows the recommended driver
sudo ubuntu-drivers install
sudo reboot
nvidia-smi                       # expected: a table with the RTX 4070 SUPER
```

### 2. NVIDIA Container Toolkit

Install it before k3s. k3s then finds the NVIDIA runtime by itself.
Source: the NVIDIA Container Toolkit install guide.

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
nvidia-ctk --version             # expected: a version number
```

### 3. Docker (to build the speech images)

```bash
sudo apt-get install -y docker.io
sudo usermod -aG docker "$USER"  # log out and in again
docker run --rm hello-world      # expected: "Hello from Docker!"
```

### 4. k3s (single node)

Write the k3s version you install in this file.

Add the address of the PC to the certificate (`--tls-san`). Without it, `kubectl` from the Mac can
refuse the connection.

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--tls-san <pc-address>" sh -
sudo k3s kubectl get node        # expected: one node, Ready
sudo grep -c nvidia /var/lib/rancher/k3s/agent/etc/containerd/config.toml   # expected: 1 or more
```

Use `kubectl` from the Mac. Copy the config and replace the address:

```bash
# on the PC
sudo cat /etc/rancher/k3s/k3s.yaml
# on the Mac: save it as ~/.kube/genai.yaml and replace 127.0.0.1 with the PC address
export KUBECONFIG=~/.kube/genai.yaml
kubectl get node     # expected: one node, Ready
```

Set `KUBECONFIG` in every new terminal. All later `kubectl` commands and the scripts in `bench/`
use it.

### 5. RuntimeClass and device plugin

```bash
kubectl apply -f k8s/nvidia-device-plugin.yaml
kubectl -n kube-system rollout status ds/nvidia-device-plugin-daemonset
kubectl describe node | grep nvidia.com/gpu     # expected: nvidia.com/gpu: 1
```

### 6. GPU test pod

```bash
kubectl apply -f k8s/gpu-test.yaml
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/gpu-test --timeout=120s
kubectl logs gpu-test            # expected: the nvidia-smi table with the RTX 4070 SUPER
kubectl delete pod gpu-test
```

## vLLM standalone on the PC

Status: ran on WSL2 on 2026-11-13 with Qwen2.5-3B-Instruct, after the k3s run (the model was in the
cache of the PVC already). The server was ready in 61 s. `/v1/models`, a chat completion (normal and
stream), and a tool call (hermes parser) worked. The numbers are the same as in the k3s pod (see
`docs/benchmarks.md`). After `docker stop`, only the desktop display (1,165 MiB) used the GPU. An
earlier run used another model (Qwen3.5-4B), see "Earlier try" in `docs/benchmarks.md`.

This step runs vLLM in Docker, outside Kubernetes, with the image that k3s uses later.

### Prepare Docker for the GPU

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu24.04 nvidia-smi   # expected: the GPU table
```

Before you start vLLM, write down the VRAM that the desktop display uses:

```bash
nvidia-smi --query-gpu=memory.used,memory.total --format=csv   # this is the "desktop display" number
```

### Start vLLM

```bash
docker run --rm --gpus all --ipc=host -p 8000:8000 \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" -v "$HOME/.cache/vllm:/root/.cache/vllm" \
  -e NVIDIA_DISABLE_REQUIRE=true \
  vllm/vllm-openai:v0.28.0 Qwen/Qwen2.5-3B-Instruct \
  --served-model-name Qwen/Qwen2.5-3B-Instruct --dtype float16 \
  --gpu-memory-utilization 0.80 --max-model-len 8192 --max-num-seqs 16 \
  --enable-prefix-caching --enable-chunked-prefill --max-num-batched-tokens 2048 \
  --speculative-config '{"method":"ngram","num_speculative_tokens":4,"prompt_lookup_max":4,"prompt_lookup_min":2}' \
  --enable-auto-tool-choice --tool-call-parser hermes
```

The first start downloads the model (about 6 GiB). The second mount keeps the compile cache, so the next
start is faster. Wait for the log line that says the server is ready.

If the model is in the `vllm-cache` PVC of k3s already, do not download it again. Scale the k3s pod
down (`kubectl scale deploy/vllm-qwen --replicas=0`, one GPU only) and mount the folders of the PVC
(`/var/lib/rancher/k3s/storage/pvc-*_default_vllm-cache/hf` and `.../vllm`) in place of the two
folders above. The compile cache of the pod holds absolute paths under `/cache/vllm`, so the first
start in Docker prints warnings (`Cubin file saved by TritonBundler not found`). They are harmless.
vLLM compiles those parts again.

How to set `--gpu-memory-utilization`: vLLM refuses to start when the free VRAM is lower than
the value times the total VRAM. The Windows desktop and other programs use VRAM, so the free VRAM
changes. If you see `Free memory on device ... is less than desired GPU memory utilization`, lower the
value by 0.01 (this is about 0.12 GiB less KV cache). If you see `No available memory for the cache
blocks`, there is too little VRAM left for the KV cache. Raise the value, or lower `--max-num-seqs`.

### Check

```bash
curl -s http://localhost:8000/v1/models        # expected: the model Qwen/Qwen2.5-3B-Instruct in the list
curl -s http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen2.5-3B-Instruct","messages":[{"role":"user","content":"Say hi"}]}'
curl -sN http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen2.5-3B-Instruct","stream":true,"messages":[{"role":"user","content":"Say hi"}]}'
```

Expected: a non-empty answer in both calls, and a stream of `data:` lines for the second call.
Tool calling: send a request with a `tools` list and `"tool_choice":"auto"`. The answer must have
`tool_calls` with the right arguments.

### Measure the VRAM

Copy these numbers into `docs/benchmarks.md` (section "VRAM") and into the table in `CLAUDE.md`:

| Number | Where to read it |
|---|---|
| Weights | vLLM log: "Model loading took ... GiB" |
| KV cache size | vLLM log: "GPU KV cache size: ... tokens" |
| Maximum concurrency | vLLM log: "Maximum concurrency for ... tokens per request" |
| Total VRAM in use | `nvidia-smi` while vLLM is idle |
| Desktop display | the number you wrote down before the start |

### If something does not fit

1. If the KV cache is too small, raise `--gpu-memory-utilization` (up to the free VRAM), or lower
   `--max-model-len` and `--max-num-seqs`. Then test the fp8 KV cache or AWQ (the configurations
   `kv_fp8` and `awq` in `bench/levers.py`). Record the choice and the reason.
2. If vLLM stops at start with an error about speculative decoding or chunked prefill, remove that
   flag from the start command and from `k8s/vllm-deployment.yaml`. Write the error and the choice
   in `docs/benchmarks.md`.

### Stop

Press `Ctrl-C`. Then run `nvidia-smi`. The GPU memory must be free (only the desktop display remains).
If you started the container with `docker run -d --name vllm-standalone`, run
`docker stop vllm-standalone && docker rm vllm-standalone` instead.

## Speech servers (STT and TTS)

Status: the servers and images were tested on a Mac (Docker, arm64). The k3s deploy ran on WSL2
on 2026-11-08 (x86 images built in WSL2): both pods became ready, both PVCs were bound, the round
trip in the cluster returned "Hello World!", and `/health` and `/metrics` answered through the
Services. Rebuild the images on the x86 machine before you deploy.

### Build the images

```bash
docker build -t genai-stt:0.1.0 speech/stt
docker build -t genai-tts:0.1.0 speech/tts
```

Import the images into k3s:

```bash
docker save genai-stt:0.1.0 | sudo k3s ctr images import -
docker save genai-tts:0.1.0 | sudo k3s ctr images import -
```

### Deploy

```bash
kubectl apply -f k8s/speech-deployment.yaml
kubectl rollout status deploy/stt-faster-whisper deploy/tts-piper
```

The first start of STT downloads the model. The first start of TTS downloads the
voice. Both go to a PVC, so later starts are fast.

### Round trip check

TTS makes speech for "hello world". STT turns it back into text.

```bash
kubectl run rt --rm -i --restart=Never --image=curlimages/curl --command -- sh -c '
  curl -s -X POST http://tts:8000/v1/audio/speech \
    -H "Content-Type: application/json" -d "{\"input\":\"hello world\"}" -o /tmp/hw.wav &&
  curl -s -X POST http://stt:8000/v1/audio/transcriptions \
    -F file=@/tmp/hw.wav -F model=whisper-1'
```

Expected: JSON with a `text` field that contains "hello world". Case can differ.

### Metrics

Both servers expose `/metrics` (`stt_requests_total`, `stt_request_duration_seconds`, `tts_requests_total`, `tts_request_duration_seconds`). Tested in Docker on a Mac.

### Known problem

`faster-whisper` 1.2.1 fails with `open() got an unexpected keyword argument
'metadata_errors'` when `av` is newer than 15.x. The file `speech/stt/requirements.txt`
pins `av==15.1.0` for this reason.

## vLLM on k3s

Status: ran on WSL2 on 2026-11-13 with Qwen2.5-3B-Instruct. The pod became ready (about 72 s on the
first start and about 51 s after a restart, with the model in the cache). From a pod in the cluster,
the Service `vllm` returned `/v1/models`, a chat completion (normal and stream), and a tool call
(hermes parser). The restart came back without a new download. The numbers are in
`docs/benchmarks.md`. The vLLM image was imported into k3s from Docker in 211 s.

### Deploy

```bash
docker pull vllm/vllm-openai:v0.28.0
docker save vllm/vllm-openai:v0.28.0 | sudo k3s ctr images import -
kubectl apply -f k8s/vllm-deployment.yaml -f k8s/vllm-service.yaml
kubectl rollout status deploy/vllm-qwen --timeout=20m
```

The first start downloads the model (about 6 GiB) to the `vllm-cache` PVC. The startup probe waits
10 minutes. On a slow network, the download can take longer, and the probe then restarts the pod.

### Download the model first

On a slow network, put the model in the cache before the pod starts. Scale the pod down, so that the
startup probe does not restart it while the download runs. Then run a pod that uses the same image
and the same PVC:

```bash
kubectl scale deploy/vllm-qwen --replicas=0
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: model-dl
spec:
  restartPolicy: Never
  enableServiceLinks: false
  containers:
    - name: dl
      image: docker.io/vllm/vllm-openai:v0.28.0
      imagePullPolicy: IfNotPresent
      command: ["hf", "download", "Qwen/Qwen2.5-3B-Instruct"]
      env:
        - name: HF_HOME
          value: /cache/hf
      volumeMounts:
        - name: cache
          mountPath: /cache
  volumes:
    - name: cache
      persistentVolumeClaim:
        claimName: vllm-cache
EOF
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/model-dl --timeout=60m
kubectl delete pod model-dl
kubectl scale deploy/vllm-qwen --replicas=1
```

A download that the probe killed leaves `*.incomplete` files in
`hf/hub/models--Qwen--Qwen2.5-3B-Instruct/blobs/` on the PVC. A new download does not reuse them.
Delete them after the download is complete.

### Check

Chat completion from a pod in the cluster:

```bash
kubectl run chat --rm -i --restart=Never --image=curlimages/curl --command -- \
  curl -s http://vllm:8000/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen2.5-3B-Instruct","messages":[{"role":"user","content":"Say hi"}]}'
```

Expected: JSON with a non-empty `choices[0].message.content`.

Restart check. The pod must come back ready without a new download:

```bash
kubectl rollout restart deploy/vllm-qwen && kubectl rollout status deploy/vllm-qwen
kubectl logs deploy/vllm-qwen --tail=-1 | grep -E 'Fetching|Downloading'   # expected: no output
```

## Open WebUI text chat

Status: deployed on WSL2 on 2026-11-08. The pod became ready (about 3 minutes, with the image
pull) and `/health` returned 200 through the Service `webui`. Not tested: the chat in the browser
(streaming) and the chat history after a restart.

### Deploy

```bash
kubectl apply -f k8s/open-webui-deployment.yaml
kubectl rollout status deploy/open-webui
```

Open WebUI settings come from the environment variables in `k8s/open-webui-deployment.yaml`
(`ENABLE_PERSISTENT_CONFIG` is `false`). A setting that you change in the web UI returns to the
file value when the pod restarts. Change the file and apply it again to change a setting for good.

### Open it from the Mac

The web UI listens on NodePort 30080 on the PC. Open an SSH tunnel. The browser then sees
`localhost`, which keeps the microphone available for voice mode.

```bash
ssh -L 8080:localhost:30080 <user>@<pc-address>
```

Open `http://localhost:8080`. Send a message. The answer must stream token by token.
Restart the pod (`kubectl rollout restart deploy/open-webui`) and check that the chat
history is still there.

## Voice mode

Status: written, untested. The audio settings are environment variables in
`k8s/open-webui-deployment.yaml`. They point to the `stt` and `tts` Services.
`AUDIO_TTS_SPLIT_ON=punctuation` turns on sentence streaming.

### Check

1. Open the web UI through the SSH tunnel (`http://localhost:8080`). The microphone works
   on `localhost`. It does not work on plain HTTP from another address.
2. In the chat, click the headphone icon (voice call). Allow the microphone.
3. Say a short English sentence. You must hear the answer. The first sentence must start
   before the model finishes the rest.
4. Listen for overlap or stutter between sentences. If you hear it, set
   `AUDIO_TTS_SPLIT_ON` to `paragraphs`, apply the file again, and write the change here.
5. Measure the time from the end of your speech to the first audio. Write the number in
   `docs/benchmarks.md`.

## Core monitoring

Status: ran on WSL2 on 2026-11-13. All 7 Prometheus targets were up (`prometheus`, `vllm`, `dcgm`,
`node-exporter`, `kube-state-metrics`, and two `speech`). The 36 dashboard queries and the 4 alert
rules use metric names that exist in Prometheus (checked by script). After 12 chat requests, the vLLM
counters moved (tokens, TTFT, inter-token latency, E2E latency, prefix cache, spec decode).
Grafana answered 401 without a login. Not checked: the panels in the browser.

The stack runs in the `monitoring` namespace: Prometheus, Grafana, DCGM exporter, Node
Exporter, and kube-state-metrics. The dashboard comes from code: `bench/gen_dash.py`.

### Deploy

Create the Grafana admin password as a Secret first. Choose your own password. It never
goes into the repository.

```bash
kubectl apply -f k8s/monitoring/00-namespace.yaml
kubectl -n monitoring create secret generic grafana-admin --from-literal=admin-password='<your password>'
kubectl apply -f k8s/monitoring/
kubectl -n monitoring rollout status deploy/prometheus deploy/grafana deploy/kube-state-metrics
kubectl -n monitoring rollout status ds/dcgm-exporter ds/node-exporter
```

### Change the dashboard

```bash
python3 bench/gen_dash.py > k8s/monitoring/31-dashboard-serving.yaml
# raise the checksum/dashboard value in k8s/monitoring/30-grafana.yaml
kubectl apply -f k8s/monitoring/31-dashboard-serving.yaml -f k8s/monitoring/30-grafana.yaml
```

### Check

1. Targets. Open an SSH tunnel and look at Prometheus:
   `kubectl -n monitoring port-forward svc/prometheus 9090:9090`, then open
   `http://localhost:9090/targets`. These jobs must be up: `prometheus`, `vllm`, `dcgm`,
   `node-exporter`, `kube-state-metrics`, `speech`.
2. Grafana. Open an SSH tunnel to the NodePort:
   `ssh -L 3000:localhost:30300 <user>@<pc-address>`. Open `http://localhost:3000` and log
   in as `admin` with your password. There is no anonymous access.
3. Open the dashboard "vLLM Serving - SLO, KV cache, GPU". Send a few chat requests. The
   panels for throughput, TTFT, and running requests must move.
4. If the target `dcgm` is down or shows no GPU, the pod may not see the GPU without a GPU request.
   Add `privileged: true` under `securityContext` of the container in
   `k8s/monitoring/20-dcgm-exporter.yaml`, apply the file, and write the change here. On WSL2 this
   was not needed: `DCGM_FI_DEV_FB_USED`, GPU utilization, and temperature had values.
   WSL2 only: the pod `node-exporter` stays in `CreateContainerError` with `path "/" is mounted on
   "/" but it is not a shared or slave mount`, because `/` is private in WSL2. Run
   `mount --make-rshared /` as root in WSL2, then delete the pod. The setting is lost at the next
   boot of WSL2. Bare-metal Ubuntu has a shared `/` and does not need this.
5. If a vLLM panel stays empty, open `http://<vllm pod>:8000/metrics` and compare the metric
   names with `bench/gen_dash.py`. The names come from the vLLM v0.28.0 source.

## Logs with Loki

Status: ran on WSL2 on 2026-11-13. Loki answered `ready`, and the queries `{app="vllm"}`,
`{app="stt"}`, `{app="tts"}`, and `{app="open-webui"}` returned lines (checked with the Loki API, not
in the Explore page of Grafana). Grafana lists the data sources Prometheus and Loki from the
provisioning file.

Loki stores logs on a PVC for 7 days. Grafana Alloy reads the logs of all pods through the
Kubernetes API and sends them to Loki. Grafana gets Loki as a data source from the
provisioning file.

### Deploy

```bash
kubectl apply -f k8s/monitoring/40-loki.yaml -f k8s/monitoring/41-alloy.yaml
kubectl apply -f k8s/monitoring/30-grafana.yaml
kubectl -n monitoring rollout restart deploy/grafana
kubectl -n monitoring rollout status deploy/loki deploy/alloy deploy/grafana
```

### Check

1. In Grafana, open Explore and choose the data source "Loki".
2. Run the query `{app="vllm"}`. You must see recent log lines of the vLLM pod.
3. Run `{app="stt"}`, `{app="tts"}`, and `{app="open-webui"}`. Each one must return lines.

## Alerts with Alertmanager

Status: ran on WSL2 on 2026-11-13. The check below passed: `TargetDown` for `kube-state-metrics`
was firing after about 100 s, Alertmanager listed it as active, and both were empty about 20 s after
the restore. A pod that Prometheus finds by pod discovery gives no alert when scaled to zero (tested
with TTS: no alert in 180 s). When the same pod runs but does not answer on its port, `TargetDown`
fires after about 80 s.

Rules are in `k8s/monitoring/50-alert-rules.yaml`: any scrape target down, vLLM preemptions
above zero, GPU temperature above 85 C, and KV cache usage above 90 percent. Alertmanager
has no notification channel. Read the alerts in its web page.

### Deploy

```bash
kubectl apply -f k8s/monitoring/50-alert-rules.yaml -f k8s/monitoring/51-alertmanager.yaml
kubectl apply -f k8s/monitoring/10-prometheus.yaml
kubectl -n monitoring rollout restart deploy/prometheus
kubectl -n monitoring rollout status deploy/alertmanager deploy/prometheus
```

### Check

Make one alert fire on purpose. Scale `kube-state-metrics` to zero. Use this target
because it is a fixed target. A pod that Prometheus finds by pod discovery (vLLM, STT, TTS)
leaves the target list when you scale it to zero, so `up` never becomes 0 for it.

```bash
kubectl -n monitoring scale deploy/kube-state-metrics --replicas=0
```

After about 2 minutes, open `http://localhost:9090/alerts` (port-forward `svc/prometheus`).
`TargetDown` must show as firing. Open Alertmanager with
`kubectl -n monitoring port-forward svc/alertmanager 9093:9093` and check
`http://localhost:9093`. The alert must be listed. Then restore it:

```bash
kubectl -n monitoring scale deploy/kube-state-metrics --replicas=1
```

After a few minutes the alert must resolve.

## Ingress with HTTPS

Status: the certificate commands were run on a Mac and verified with `openssl verify`.
The Ingress file passes `kubeconform`. The cluster steps are written, untested.

Traefik is the k3s default Ingress controller. The host names are `webui.genai.test` and
`grafana.genai.test`. The `.test` top-level domain is reserved, so it never points to a real site.

### 1. Make a local certificate authority (on the Mac)

Keep these files outside the repository. The folder `~/.genai-certs` is outside it.

```bash
mkdir -p ~/.genai-certs && cd ~/.genai-certs
openssl genrsa -out ca.key 4096
openssl req -x509 -new -key ca.key -sha256 -days 825 -subj "/CN=genai local CA" -out ca.crt
openssl genrsa -out tls.key 2048
openssl req -new -key tls.key -subj "/CN=genai.test" -out tls.csr
printf "subjectAltName=DNS:webui.genai.test,DNS:grafana.genai.test\nextendedKeyUsage=serverAuth\nbasicConstraints=CA:FALSE\n" > ext.cnf
openssl x509 -req -in tls.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out tls.crt -days 825 -sha256 -extfile ext.cnf
openssl verify -CAfile ca.crt tls.crt
```

### 2. Trust the CA on the Mac

This command needs `sudo`. Run it yourself.

```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ~/.genai-certs/ca.crt
```

### 3. Put the certificate in the cluster

An Ingress can use a Secret only in its own namespace. Make the same Secret in two namespaces.

```bash
kubectl -n default create secret tls genai-tls --cert=$HOME/.genai-certs/tls.crt --key=$HOME/.genai-certs/tls.key
kubectl -n monitoring create secret tls genai-tls --cert=$HOME/.genai-certs/tls.crt --key=$HOME/.genai-certs/tls.key
kubectl apply -f k8s/ingress/ingress.yaml
```

### 4. Point the host names to the PC

On the Mac, add one line to `/etc/hosts` (needs `sudo`). Use the address of the PC:

```
<pc-address> webui.genai.test grafana.genai.test
```

### Check

1. Open `https://webui.genai.test` and `https://grafana.genai.test`. Both pages must load with no
   certificate warning.
2. Open the voice call screen at `https://webui.genai.test`. The browser must let you use the
   microphone. Say a sentence and listen for the answer. No SSH tunnel is needed now.

## Benchmark harness

Status: ran on WSL2 on 2026-11-13 for 6 configurations (all 8 workload and concurrency runs each, no
failed request). The run found a bug: the `custom` dataset needs pandas, which the vLLM image does not
have, so the `chat` workload now uses a `sharegpt` dataset that `bench/run.sh` makes from
`bench/prompts`. On WSL2 set `VLLM_USE_V2_MODEL_RUNNER=0` for configurations without speculative
decoding (`kubectl set env deploy/vllm-qwen VLLM_USE_V2_MODEL_RUNNER=0`). Without it, the engine stops
with `RuntimeError: UVA is not available`. Remove it after the run. A long run needs an open session to
the PC (see "Remote access"), because WSL2 stops when no session is open.

`bench/run.sh <label>` runs `vllm bench serve` inside the vLLM pod for three workloads at
concurrency 1, 8, and 16. It uses seed 0, 3 warmup requests, 24, 96, and 160 prompts for
concurrency 1, 8, and 16, and `--ignore-eos`. The workloads are random tokens (input 512, output 128,
engine only), chat text (output 128), and a shared prefix (prefix 1024, input 256, output 128,
prefix caching, concurrency 1 and 8 only). The chat text is the 28 prompts in `bench/prompts`. The
flags come from the vLLM v0.28.0 source. Raw JSON goes to `bench/results/<label>/`. With
`--max-num-seqs 16` the run at concurrency 16 is at the limit of the engine. Read the queue time
and do not take it as a failure of a configuration.

```bash
bench/run.sh baseline
python3 bench/summarize.py baseline                # table, saved as summary.md
kubectl port-forward svc/vllm 8000:8000 &          # for the quality check
python3 bench/quality_check.py --label baseline    # 14 English and Thai prompts, temperature 0, 256 tokens
```

Paste the table in `docs/benchmarks.md` with the vLLM version, driver, model, and flags.

## Optimization levers

Status: measured on WSL2 on 2026-11-13: `baseline`, `deployed`, `spec_ngram`, `spec_draft`, `compile`,
and `awq`. The results are in `docs/benchmarks.md`. `sched`, `kv_fp8`, and `min_latency` use a GPU memory
utilization of 0.92 and do not start on this PC: the free VRAM at start is 10.79 GiB, and 0.92 needs 11.03
GiB. The model `Qwen/Qwen2.5-3B-Instruct-AWQ` and the draft model `Qwen/Qwen2.5-0.5B-Instruct` must be in the
cache first (see "Download the model first", with the model names changed). The final flags are not chosen.

Each configuration is a full argument list for the vLLM container. `baseline` is the plain engine.
The others change one thing, or a few things together (`min_latency`). `deployed` is the argument
list of `k8s/vllm-deployment.yaml`.

```bash
python3 bench/levers.py list
python3 bench/levers.py apply baseline
bench/run.sh baseline && python3 bench/quality_check.py --label baseline

# repeat for each configuration, for example:
python3 bench/levers.py apply spec_ngram
bench/run.sh spec_ngram && python3 bench/quality_check.py --label spec_ngram
```

Configurations: `baseline`, `awq`, `sched`, `kv_fp8`, `spec_ngram`, `spec_draft`, `compile`,
`deployed`, and `min_latency`. Read the VRAM of each one from `nvidia-smi` and the vLLM log. A
configuration is lossless when the quality check gives the same answers as the baseline. The first
start of `compile` and `min_latency` builds the compile cache and takes several minutes. If a
configuration does not start, write the error in `docs/benchmarks.md` and go on to the next one.

Choose the best lossless combination. Write the reasons in `docs/benchmarks.md`. Then put the
final flags in `k8s/vllm-deployment.yaml`, apply it, and run `bench/smoke_test.sh`.

## Full smoke test

Status: the pass and fail logic ran on a Mac with a fake `curl` (all pass gives exit 0, a wrong
answer gives exit 1). `shellcheck` shows no real warning. The real run is untested.

```bash
sh bench/smoke_test.sh <pc-address>              # CA path default: ~/.genai-certs/ca.crt
```

It takes about one minute and prints `PASS` or `FAIL` for each check:

1. vLLM chat completion returns a non-empty answer.
2. TTS to STT round trip returns "hello world".
3. Prometheus reports the targets `vllm`, `stt`, `tts`, `dcgm`, `node-exporter`, and `kube-state-metrics` as up.
4. Loki and Alertmanager are ready.
5. Open WebUI and Grafana answer over HTTPS through the Ingress. On EC2 without the Ingress, run `sh bench/smoke_test.sh --no-https` to skip this check.

The first four groups run in a temporary pod (`curlimages/curl`), because the Services are
ClusterIP only. The HTTPS checks run on the Mac. The exit code is 1 if any check fails.

## Thai TTS (bonus)

Status: the comparison scripts are written and were never run. You run them yourself, because
the image installs code from GitHub. Do this after voice mode works in English.

Two candidates make speech for the same 8 Thai sentences (tones, numbers, mixed English words).
The facts of the candidates are in `docs/benchmarks.md`, section "Thai TTS".

```bash
cd bench/thai_tts
docker build -t genai-thai-tts:dev .
mkdir -p ../results/thai-tts "$HOME/.cache/genai-thai-voices"

# Candidate 1: Piper voice th_TH-tsync2-medium (63 MB)
docker run --rm --entrypoint python -v "$HOME/.cache/genai-thai-voices:/voices" genai-thai-tts:dev \
  -m piper.download_voices th_TH-tsync2-medium --download-dir /voices
docker run --rm -v "$HOME/.cache/genai-thai-voices:/voices" -v "$PWD/../results/thai-tts:/out" \
  genai-thai-tts:dev piper-th

# Candidate 2: FastThaiG2P with the Thai Kokoro model (about 326 MB, downloads on the first run)
docker run --rm -v genai-thai-cache:/root/.cache -v "$PWD/../results/thai-tts:/out" \
  genai-thai-tts:dev fastthaig2p
```

Each command prints a Markdown table (time to first audio and RTF for each sentence). The WAV
files are in `bench/results/thai-tts/`. Git ignores that folder. Listen to all sentences of both
candidates, then choose one. Paste the tables in `docs/benchmarks.md`.

The timings from a Mac or another machine are only good to compare the two candidates with each
other. Run the same commands on the target machine for the final numbers.

After you choose a voice, the work is: let `speech/tts/server.py` pick the voice file from the
`voice` field of the request, add the voice to the voices folder, and set `AUDIO_TTS_VOICE` in
Open WebUI. Do that only after the choice.

## Rehearsal on WSL2 (before the real test)

Status: partly tested on WSL2 (2026-11-08). The section "PC as a GPU node" ran on WSL2 and passed
(see "Observed on WSL2" below). The other sections are not run yet. WSL2 is not bare-metal Linux,
so write every result of this run as "tested on WSL2". It does not replace the test on Ubuntu or
on EC2. The test on Ubuntu or EC2 stays required for the parts that differ.

### What is different in WSL2

| Topic | WSL2 | What to do |
|---|---|---|
| GPU driver | The Windows driver gives the GPU to WSL2. | Do not install a Linux driver. Skip step 1 of "PC as a GPU node". `nvidia-smi` must work inside WSL2. |
| Memory | WSL2 uses half of the RAM by default. | Set the limit in `.wslconfig` (below). |
| Services | k3s needs systemd. | Turn on systemd (below). |
| Docker | Docker Desktop with its own Kubernetes breaks the GPU in the cluster. | Install `docker.io` inside WSL2 (step 3 of "PC as a GPU node"). Do not use Docker Desktop. |
| Device plugin | v0.20.1 detects the platform `wsl` and registers the GPU (observed). | If the node shows no `nvidia.com/gpu`, see the failure list below. |
| DCGM exporter | Not confirmed on WSL2. | If the pod fails or shows no GPU data, mark the GPU row of the dashboard and the `dcgm` target as "not testable on WSL2". |
| `kubectl` | The `kubectl` that k3s installs reads the file of root by default. | Copy the file to `~/.kube/config` and set `export KUBECONFIG=$HOME/.kube/config` (put it in `~/.bashrc`). |
| Network | NAT. A NodePort can be unreachable from Windows. | Use `kubectl port-forward` (below). Do not test the HTTPS Ingress here. |
| Disk | The distribution disk is on `C:` by default. | Move it with `wsl --manage Ubuntu-24.04 --move D:\vLLM\wsl\Ubuntu-24.04` (below). |
| Numbers | Windows can still use the GPU. | VRAM and benchmark numbers are not final. |

### Prepare Windows and WSL2

1. Install the latest NVIDIA driver for Windows.
2. In PowerShell, install Ubuntu (check the name with `wsl --list --online`):
   ```powershell
   wsl --install -d Ubuntu-24.04
   ```
3. Set the memory limit. Make the file `%UserProfile%\.wslconfig`:
   ```
   [wsl2]
   memory=24GB
   swap=8GB
   ```
4. In the Ubuntu terminal, turn on systemd, then restart WSL2:
   ```bash
   printf "[boot]\nsystemd=true\n" | sudo tee /etc/wsl.conf
   ```
   ```powershell
   wsl --shutdown
   ```
5. Check the GPU inside WSL2: `nvidia-smi` must show the RTX 4070 SUPER.
6. (Optional) Move the distribution disk to another drive. Close every WSL2 window, then:
   ```powershell
   wsl --shutdown
   wsl --manage Ubuntu-24.04 --move D:\vLLM\wsl\Ubuntu-24.04
   ```
   If the move says `ERROR_SHARING_VIOLATION`, WSL2 is still running. Run `wsl --shutdown` and
   move again at once, without another `wsl` command in between.

### Get the code into WSL2 without a push

Nothing goes to GitHub. With SSH access (next section), send the project from the Mac. The project
folder in this run is `D:\vLLM\vLLM-GenAI` (`/mnt/d/vLLM/vLLM-GenAI` in WSL2):

```bash
cd ~/Workspaces/Code/vLLM/vLLM-GenAI
COPYFILE_DISABLE=1 tar czf - --exclude=.DS_Store --exclude=.git/config . | ssh -i ~/.ssh/<key> <windows-user>@<pc-ip> \
  'wsl -d Ubuntu-24.04 -- bash -lc "mkdir -p /mnt/d/vLLM/vLLM-GenAI && tar xzf - -C /mnt/d/vLLM/vLLM-GenAI --warning=no-unknown-keyword"'
```

Work on the Mac and send the project again after each change. Do not edit the copy on the PC.
Then check that `git rev-parse HEAD` in the copy equals the one on the Mac. The first time, run
`git config core.fileMode false` in the copy, because the Windows disk does not keep Unix modes.
The command above keeps `.git/config` of the PC, so this setting stays. Without that option, the
Mac file replaces it and `git status` shows every file as changed (only the mode).
The warnings `Ignoring unknown extended header keyword` come from macOS and are harmless.

Without SSH, make a bundle on the Mac (`git bundle create /tmp/vllm-genai.bundle --all`), move the
file to the PC, and run `git clone <bundle> vLLM-GenAI` in WSL2.

### Remote access from the Mac (optional)

This lets the agent or you run the steps from the Mac. It uses the OpenSSH Server of Windows.

1. PowerShell as Administrator on the PC:
   ```powershell
   Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
   Set-Service -Name sshd -StartupType Automatic
   Start-Service sshd
   ```
2. On the Mac, make a key and put the public key (one line) in
   `C:\ProgramData\ssh\administrators_authorized_keys` on the PC (the account is an
   administrator). Then run `icacls.exe C:\ProgramData\ssh\administrators_authorized_keys /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"`.
3. The firewall rule `OpenSSH-Server-In-TCP` applies only to the profile `Private`. If the network
   is `Public`, the Mac cannot connect (the symptom is a timeout). Fix it for the home network only:
   ```powershell
   Set-NetFirewallRule -Name OpenSSH-Server-In-TCP -Profile Private,Public -RemoteAddress 192.168.1.0/24
   ```
4. Do not set `DefaultShell` to `bash.exe`. That file does not exist on current WSL. sshd then
   refuses the user ("shell ... does not exist"). Keep the default shell and call WSL in the command:
   ```bash
   ssh -i ~/.ssh/<key> <windows-user>@<pc-ip> 'wsl -d Ubuntu-24.04 -- bash -s' <<'EOF'
   echo "this script runs in WSL2"
   EOF
   ```
   Send scripts through stdin. A command in quotes is expanded by a shell on the way, and the
   result is wrong. To run a command as root without a password, use `wsl -d Ubuntu-24.04 -u root -- ...`.
5. When the run is over, take the access away (PowerShell as Administrator):
   ```powershell
   Set-NetFirewallRule -Name OpenSSH-Server-In-TCP -Profile Private -RemoteAddress Any
   Stop-Service sshd; Set-Service sshd -StartupType Disabled
   Remove-Item C:\ProgramData\ssh\administrators_authorized_keys
   ```

### Run the steps

Run the commands in WSL2 with `kubectl` inside WSL2 (with `KUBECONFIG` set, see the table).
Follow the sections in this order, with the changes from the table above:

1. "PC as a GPU node": skip step 1, do steps 2 to 6.
2. "vLLM standalone on the PC".
3. "Speech servers", "vLLM on k3s", "Open WebUI text chat", "Voice mode".
4. "Core monitoring", "Logs with Loki", "Alerts with Alertmanager".
5. "Benchmark harness" and "Full smoke test" with `sh bench/smoke_test.sh --no-https`. The check for the
   target `dcgm` can fail on WSL2. That is expected if DCGM does not work there.

Open the pages with port-forward, in two terminals. Then open them in the Windows browser.
The address is `localhost`, so the microphone works:

```bash
kubectl port-forward svc/webui 8080:8080       # http://localhost:8080
kubectl -n monitoring port-forward svc/grafana 3000:3000   # http://localhost:3000
```

### Observed on WSL2

| Step | Result |
|---|---|
| `nvidia-smi` in WSL2 | RTX 4070 SUPER visible. About 1 GB of VRAM is used by the Windows desktop. |
| NVIDIA Container Toolkit 1.20.1 | Installed. |
| Docker 29.1.3 with `--gpus all` | A container sees the GPU. |
| k3s v1.37.2+k3s1 | Node `Ready`. The NVIDIA runtime is in the containerd config. |
| Device plugin v0.20.1 | Log says `Detected platform: wsl`. The node reports `nvidia.com/gpu: 1`. |
| `k8s/gpu-test.yaml` | The pod ran `nvidia-smi` and ended with `Succeeded`. |
| vLLM standalone (Docker) | Ran with an earlier model (Qwen3.5-4B): API, stream, and tool call passed, VRAM measured. See `docs/benchmarks.md`. Not run with Qwen2.5-3B-Instruct yet. |
| Speech pods on k3s | Ready in 27 s. Round trip in the cluster returned "Hello World!". `/metrics` reachable. |
| Open WebUI on k3s | Pod ready. `/health` returned 200 through the Service. |
| Images into k3s | `docker save <image> \| k3s ctr images import -` (the vLLM image, 28.8 GB, took 211 s). |
| vLLM on k3s, monitoring | Applied. Result not seen (the SSH connection dropped). Check these first when you continue. |

### If the node shows no GPU

1. `kubectl -n kube-system logs ds/nvidia-device-plugin-daemonset`. Read the first error lines.
2. Check that the pod uses `runtimeClassName: nvidia` (the file does).
3. Try a newer device plugin tag or the build from the main branch. Change the image in
   `k8s/nvidia-device-plugin.yaml`, and write the version that works in this file.
4. If nothing works, write the error in this file and stop the GPU part of the rehearsal. The
   parts that do not need the GPU (speech, Open WebUI, monitoring, logs, alerts) still run.

### Record the result

Write what passed and what failed, with the label "WSL2", in the section of each step. Keep the
list of "not testable on WSL2" items. Repeat only those items on Ubuntu or on EC2.

## If you run on EC2

The local PC is the main machine. You can run the same stack on a rented GPU machine. The steps
in this runbook stay the same. Check these differences first.

### Differences to check

| Topic | What to check |
|---|---|
| fp8 and bf16 | A GPU older than Ada has no fp8. A GPU older than Ampere has no bf16. On such a GPU use `--dtype float16` and do not use the fp8 levers. |
| VRAM | The size is different. Calculate the VRAM budget again and set `--gpu-memory-utilization` and `--max-model-len` for it. No desktop display uses the GPU, so more VRAM is free. |
| Quota | A new AWS account has a quota of zero for GPU instances. Ask for the quota "Running On-Demand G and VT instances" in the region you use. The quota counts vCPU. Wait for the support case to close. |
| Cost | You pay for each hour. Set an AWS Budget alert before the first launch. Stop the machine when you do not use it. |
| Microphone | The browser blocks the microphone on plain HTTP. Open the web UI through an SSH tunnel (it is then `localhost`) or through HTTPS. |

### Steps

1. **Budget.** Create a monthly cost budget with email alerts.
2. **Quota.** Make the quota request. Check the region name in the top right of the console.
3. **SSH key.** Make a key on your computer and import the public key in EC2, section "Key
   pairs", in the same region. Never put the private key in the repository.
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/vllm-genai -C "vllm-genai-ec2"
   ```
4. **Launch.** Choose an Ubuntu LTS image and a GPU instance that fits the table above. Use at
   least 100 GB of disk (model, images, and caches). Let SSH in from your own address only.
5. **Install.** Connect with `ssh -i ~/.ssh/vllm-genai ubuntu@<public-address>`. Follow the
   sections from "PC as a GPU node" to "Alerts with Alertmanager". Skip "Ingress with HTTPS".
6. **Open the pages** through an SSH tunnel:
   ```bash
   ssh -i ~/.ssh/vllm-genai -L 8080:localhost:30080 -L 3000:localhost:30300 ubuntu@<public-address>
   ```
   Open `http://localhost:8080` (web UI) and `http://localhost:3000` (Grafana).
7. **Stop.** Use "Stop instance" when you finish. The disk stays and costs a small amount. Use
   "Terminate" only when you want to delete everything. Deploy again with the same files.
