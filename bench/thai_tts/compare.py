#!/usr/bin/env python3
"""Make speech for the same Thai sentences with each candidate and time it.

Run it in Docker (see docs/setup.md, section "Thai TTS"). It writes one WAV file per
candidate and sentence, so that you can listen, and it prints a Markdown table.

  piper-th     Piper voice th_TH-tsync2-medium. Run through the Piper CLI for each
               sentence, the same way speech/tts/server.py runs it.
  fastthaig2p  FastThaiG2P with the Thai Kokoro-82M ONNX model. The model is loaded
               once, as a server would do.

Time to first audio: both candidates make a whole sentence before they return it. So the
time to first audio of a sentence is the time to make that sentence ("wall").
RTF is the synthesis time divided by the audio length. Below 1 is faster than real time.
"""
import argparse
import json
import subprocess
import sys
import time
import wave
from pathlib import Path
from statistics import mean

HERE = Path(__file__).parent
PIPER_VOICE = "th_TH-tsync2-medium"


def audio_seconds(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def run_piper(sentences, out, voices):
    model = Path(voices) / f"{PIPER_VOICE}.onnx"

    def synth(text, wav):
        subprocess.run(
            [sys.executable, "-m", "piper", "--model", str(model), "--output-file", str(wav)],
            input=text.encode(), check=True, capture_output=True,
        )

    synth(sentences[0]["text"], out / "warmup.wav")  # warm the disk cache
    return synth, {"load_s": None, "note": "model is loaded on every call"}


def run_fastthai(sentences, out, voices):
    from fastthaig2p import TTS

    TTS()  # first call downloads the model into the cache. It is not timed.
    t = time.perf_counter()
    tts = TTS()
    load_s = time.perf_counter() - t
    tts.synthesize(sentences[0]["text"], str(out / "warmup.wav"))  # first call is slow

    def synth(text, wav):
        tts.synthesize(text, str(wav))

    return synth, {"load_s": load_s, "note": "model is loaded once"}


CANDIDATES = {"piper-th": run_piper, "fastthaig2p": run_fastthai}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate", choices=sorted(CANDIDATES))
    ap.add_argument("--out", default="/out")
    ap.add_argument("--voices", default="/voices")
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sentences = json.loads((HERE / "sentences.json").read_text())
    synth, info = CANDIDATES[a.candidate](sentences, out, a.voices)

    rows = []
    for s in sentences:
        wav = out / f"{a.candidate}_{s['id']}.wav"
        t = time.perf_counter()
        synth(s["text"], wav)
        wall = time.perf_counter() - t
        dur = audio_seconds(wav)
        rows.append({"id": s["id"], "kind": s["kind"], "wall_s": wall, "audio_s": dur, "rtf": wall / dur})
    (out / "warmup.wav").unlink(missing_ok=True)

    (out / f"{a.candidate}.json").write_text(json.dumps({"info": info, "rows": rows}, indent=2))
    print(f"### {a.candidate} ({info['note']})")
    if info["load_s"] is not None:
        print(f"Model load time: {info['load_s']:.2f} s\n")
    print("| sentence | kind | time to first audio (s) | audio (s) | RTF |")
    print("|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['id']} | {r['kind']} | {r['wall_s']:.2f} | {r['audio_s']:.2f} | {r['rtf']:.2f} |")
    print(f"| mean | | {mean(r['wall_s'] for r in rows):.2f} | {mean(r['audio_s'] for r in rows):.2f} "
          f"| {mean(r['rtf'] for r in rows):.2f} |")


if __name__ == "__main__":
    main()
