#!/usr/bin/env python3
"""Measure the time from the end of speech to the first audio of the answer.

Run it inside the vLLM pod, which can reach the Services by name:

    kubectl exec -i deploy/vllm-qwen -- python3 - < bench/voice_latency.py

Steps, as Open WebUI does them in the voice mode:
  1. STT: the sound of the question becomes text.
  2. LLM: the answer streams. The time stops at the end of the first sentence.
  3. TTS: the first sentence becomes sound. The server returns the whole file, so the time stops at its end.
The sound of the question is made by the TTS server and is not timed. There is no microphone, so the
time to detect the end of speech is not part of the result.
"""
import json
import re
import statistics
import time
import urllib.request
import uuid

STT = "http://stt:8000/v1/audio/transcriptions"
TTS = "http://tts:8000/v1/audio/speech"
LLM = "http://vllm:8000/v1/chat/completions"
MODEL = "Qwen/Qwen2.5-3B-Instruct"
QUESTIONS = ["What is the capital of France?", "Give me two tips to sleep better.",
             "What is a KV cache?", "Tell me a short joke about computers."]
RUNS = 5


def post_json(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=120)


def stt(wav):
    b = uuid.uuid4().hex
    body = (f'--{b}\r\nContent-Disposition: form-data; name="model"\r\n\r\nwhisper-1\r\n'
            f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="q.wav"\r\n'
            f'Content-Type: audio/wav\r\n\r\n').encode() + wav + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(STT, body, {"Content-Type": f"multipart/form-data; boundary={b}"})
    return json.load(urllib.request.urlopen(req, timeout=120))["text"].strip()


def first_sentence(text):
    """Stream the answer and return (seconds to the first token, seconds to the first sentence, sentence)."""
    t0 = time.perf_counter()
    first = None
    out = ""
    with post_json(LLM, {"model": MODEL, "stream": True, "max_tokens": 128, "temperature": 0,
                         "messages": [{"role": "user", "content": text}]}) as r:
        for line in r:
            line = line.decode().strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            delta = json.loads(line[6:])["choices"][0]["delta"].get("content") or ""
            if delta and first is None:
                first = time.perf_counter() - t0
            out += delta
            m = re.search(r"[.!?](\s|$)", out)
            if m:
                return first, time.perf_counter() - t0, out[:m.end()].strip()
    return first, time.perf_counter() - t0, out.strip()


def main():
    wavs = {q: post_json(TTS, {"input": q}).read() for q in QUESTIONS}
    rows = []
    for i in range(RUNS + 1):                      # the first run is a warm-up
        for q in QUESTIONS:
            t = time.perf_counter()
            text = stt(wavs[q])
            t_stt = time.perf_counter() - t
            ttft, t_sent, sentence = first_sentence(text)
            t = time.perf_counter()
            post_json(TTS, {"input": sentence}).read()
            t_tts = time.perf_counter() - t
            if i:
                rows.append((t_stt, ttft, t_sent, t_tts, t_stt + t_sent + t_tts))
    names = ["STT", "LLM first token", "LLM first sentence", "TTS of the sentence", "total to first audio"]
    print(f"{len(rows)} runs ({len(QUESTIONS)} questions x {RUNS}), seconds")
    for n, col in zip(names, zip(*rows)):
        s = sorted(col)
        print(f"{n:22s} p50 {statistics.median(s):.2f}  max {s[-1]:.2f}")


main()
