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
