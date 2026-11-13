# 05: STT and TTS servers

**What to build:** Two small servers with OpenAI-compatible audio APIs run as pods on CPU: STT (faster-whisper) and TTS (Piper, English voice). A `curl` round trip turns "hello world" into speech and back into text.

**Blocked by:** 01

**Status:** ready-for-agent

**Test status:** servers tested in Docker on a Mac (arm64). On WSL2 (2026-11-08) the k3s deploy passed: pods ready, PVCs bound, round trip in the cluster returned "Hello World!", `/metrics` reachable. Two boxes ticked earlier stay as they are. The other boxes wait for Ubuntu or EC2.

- [x] STT server: `/v1/audio/transcriptions` and `/health`, faster-whisper on CPU (English model, int8, greedy decoding, fixed language, VAD filter, no previous-text conditioning), settings from environment variables
- [x] TTS server: `/v1/audio/speech` and `/health`, Piper on CPU, English voice, no trailing sentence silence, serialized synthesis
- [x] Both images built before deploy (no package installation at pod start), versions pinned
- [x] Deployments with no GPU request, and ClusterIP Services named `stt` and `tts`
- [x] Model and voice files on a PersistentVolumeClaim
- [x] Round trip: TTS output for "hello world" sent to STT returns text that contains "hello world"
- [ ] The setup runbook has the build, deploy, and round-trip steps

**Notes**
- Round trip in Docker on the Mac: TTS made speech for "hello world", STT returned `Hello World!`.
- The manifest passes `kubeconform -strict`. This checks the schema only.
- Open: build the images on the x86 machine, import them into k3s, deploy, and run the round trip in the cluster.
- Settings use our own names: `STT_*` and `TTS_*` environment variables. The transcription route is a normal `def` route, so `/health` answers during a long transcription (checked in Docker: 2 ms during a 3.6 s transcription).
- The base image uses the tag `python:3.12-slim` (not a digest). Python packages are pinned.
