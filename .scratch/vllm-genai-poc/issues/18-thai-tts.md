# 18: Thai TTS voice (bonus)

**What to build:** Voice mode can answer in Thai with a Thai TTS voice.

**Blocked by:** 06

**Status:** ready-for-agent

**Test status:** candidates researched from primary sources (two found). The comparison scripts in `bench/thai_tts/` are written and never run. The user runs them, listens, and chooses. No box is ticked.

- [ ] At least 2 Thai TTS candidates tested with the same Thai sentences (tones, numbers, mixed English words): quality, time to first audio, license, CPU or GPU use
- [ ] The user listens and chooses one
- [ ] The chosen voice is served through the same OpenAI-compatible TTS API and connected to Open WebUI
- [ ] Results recorded in the benchmarks document
