# 06: Voice mode in Open WebUI

**What to build:** The user opens the voice call screen in Open WebUI, speaks English, and hears the answer. Speech starts with the first sentence while the model still writes the rest.

**Blocked by:** 04, 05

**Status:** ready-for-agent

**Test status:** written, untested. Environment variables and runbook steps are in place. No box is ticked: every item needs the browser on the real cluster.

- [ ] Open WebUI audio settings point to the `stt` and `tts` Services through environment variables
- [ ] Sentence-level streaming of TTS turned on
- [ ] Voice call works in the browser through the SSH tunnel (`localhost`, so the microphone is allowed)
- [ ] No overlap or stutter between sentences; if it occurs, the fallback setting is applied and recorded
- [ ] The time from end of speech to first audio is measured and recorded in the benchmarks document
- [ ] The setup runbook has the voice settings and a voice check step
