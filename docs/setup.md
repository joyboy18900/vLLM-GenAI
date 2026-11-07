# Setup runbook

Each section lists the steps for one part of the stack. A step is "tested" only
when someone ran it on the target machine. Sections marked "written, untested"
did not run on the PC yet.

## Speech servers (STT and TTS)

Status: the servers and images were tested on a Mac (Docker, arm64). The k3s
manifest is written, untested. Rebuild the images on the x86 machine before you deploy.

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

Status: written, untested. The flags in `k8s/vllm-deployment.yaml` are provisional.
Ticket 02 must measure them on the PC first. Then update the file.

Sources for the flags: the Qwen3.5-4B model card (reasoning parser `qwen3`, tool parser
`qwen3_coder`, `--language-model-only`) and the vLLM docs (`--default-chat-template-kwargs`).

### Deploy

```bash
docker pull vllm/vllm-openai:v0.28.0
docker save vllm/vllm-openai:v0.28.0 | sudo k3s ctr images import -
kubectl apply -f k8s/vllm-deployment.yaml -f k8s/vllm-service.yaml
kubectl rollout status deploy/vllm-qwen --timeout=20m
```

The first start downloads the model to the `vllm-cache` PVC.

### Check

Chat completion from a pod in the cluster:

```bash
kubectl run chat --rm -i --restart=Never --image=curlimages/curl --command -- \
  curl -s http://vllm:8000/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen3.5-4B","messages":[{"role":"user","content":"Say hi"}]}'
```

Expected: JSON with a non-empty `choices[0].message.content`.

Restart check. The pod must come back ready without a new download:

```bash
kubectl rollout restart deploy/vllm-qwen && kubectl rollout status deploy/vllm-qwen
kubectl logs deploy/vllm-qwen | grep -i download   # expected: no new download
```

## Open WebUI text chat

Status: written, untested.

### Deploy

```bash
kubectl apply -f k8s/open-webui-deployment.yaml
kubectl rollout status deploy/open-webui
```

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

Status: written, untested. Checked offline: `kubeconform` on the manifests, `promtool check config`
on the Prometheus config, and `promtool check rules` on all 36 dashboard queries (syntax only).

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
4. If a vLLM panel stays empty, open `http://<vllm pod>:8000/metrics` and compare the metric
   names with `bench/gen_dash.py`. The names come from the vLLM v0.28.0 source.

## Logs with Loki

Status: written, untested. Checked offline: `kubeconform`, `loki -verify-config`, and
`alloy fmt` (syntax only).

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

Status: written, untested. Checked offline: `kubeconform`, `promtool check config` (it also
loads the rules), and `amtool check-config`.

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

Status: the Python scripts ran against a fake server and fake data on a Mac (logic only).
`bench/run.sh` is written, untested. It needs the real cluster.

`bench/run.sh <label>` runs `vllm bench serve` inside the vLLM pod for three workloads at
concurrency 1, 8, and 16: random tokens (engine only), real chat text, and a long shared prefix
(prefix caching). It uses a fixed seed and 3 warmup requests. The flags come from the vLLM v0.28.0
source. Raw JSON goes to `bench/results/<label>/`.

```bash
bench/run.sh baseline
python3 bench/summarize.py baseline                # table, saved as summary.md
kubectl port-forward svc/vllm 8000:8000 &          # for the quality check
python3 bench/quality_check.py --label baseline    # 14 English and Thai prompts at temperature 0
```

Paste the table in `docs/benchmarks.md` with the vLLM version, driver, model, and flags.

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
5. Open WebUI and Grafana answer over HTTPS through the Ingress.

The first four groups run in a temporary pod (`curlimages/curl`), because the Services are
ClusterIP only. The HTTPS checks run on the Mac. The exit code is 1 if any check fails.
