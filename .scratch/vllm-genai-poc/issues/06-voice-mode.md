# 06: Voice mode in Open WebUI

**What to build:** The user opens the voice call screen in Open WebUI, speaks English, and hears the answer. Speech starts with the first sentence while the model still writes the rest.

**Blocked by:** 04, 05

**Status:** ready-for-agent

**Test status:** on 2026-11-13 the live Deployment of Open WebUI had the `AUDIO_*` variables that point to the `stt` and `tts` Services, and `AUDIO_TTS_SPLIT_ON=punctuation`. A read-aloud click in the browser reached the TTS pod (HTTP 200). Not tested: the voice call, the microphone, the overlap check, and the time to first audio (they need a real microphone and a person who listens).

- [x] Open WebUI audio settings point to the `stt` and `tts` Services through environment variables
- [x] Sentence-level streaming of TTS turned on
- [ ] Voice call works in the browser through the SSH tunnel (`localhost`, so the microphone is allowed)
- [ ] No overlap or stutter between sentences; if it occurs, the fallback setting is applied and recorded
- [ ] The time from end of speech to first audio is measured and recorded in the benchmarks document
- [ ] The setup runbook has the voice settings and a voice check step
