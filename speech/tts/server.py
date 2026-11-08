"""Text to speech service.

It offers the OpenAI speech route on top of Piper. Piper runs on the CPU, so it takes
no VRAM from vLLM. Each request runs the Piper command line tool, which writes a WAV
file to its standard output.

All settings come from TTS_* environment variables.
"""
import os
import subprocess
import sys
import threading
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel

VOICE_FILE = os.getenv("TTS_VOICE_FILE", "/voices/en_US-lessac-medium.onnx")
# Open WebUI sends one request for each sentence. Piper adds silence after a sentence
# by default. Zero gives gapless speech.
SENTENCE_SILENCE = os.getenv("TTS_SENTENCE_SILENCE", "0.0")
# Open WebUI sends its sentence requests at the same time. Each one starts a Piper
# process that needs a lot of memory. Run only this many at once.
MAX_PARALLEL = int(os.getenv("TTS_MAX_PARALLEL", "1"))
CPU_THREADS = os.getenv("TTS_CPU_THREADS", "2")

_slots = threading.BoundedSemaphore(MAX_PARALLEL)

REQUESTS = Counter("tts_requests_total", "Speech requests", ["status"])
LATENCY = Histogram(
    "tts_request_duration_seconds", "Speech request duration",
    buckets=(0.1, 0.25, 0.5, 1, 2, 4, 8, 16),
)

app = FastAPI(title="tts")


class SpeechRequest(BaseModel):
    input: str
    model: str | None = None  # accepted and ignored
    voice: str | None = None  # accepted and ignored: one voice is loaded
    response_format: str | None = "wav"  # Piper makes WAV only
    speed: float | None = None


@app.middleware("http")
async def measure(request: Request, call_next):
    if request.url.path != "/v1/audio/speech":
        return await call_next(request)
    started = time.perf_counter()
    status = "500"
    try:
        response = await call_next(request)
        status = str(response.status_code)
        return response
    finally:
        REQUESTS.labels(status).inc()
        LATENCY.observe(time.perf_counter() - started)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health():
    return {"status": "ok", "voice": os.path.basename(VOICE_FILE)}


def synthesize(text: str, speed: float | None) -> bytes:
    command = [
        sys.executable, "-m", "piper", "--model", VOICE_FILE,
        "--sentence-silence", SENTENCE_SILENCE, "--output-file", "-",
    ]
    if speed and speed > 0:
        command += ["--length-scale", str(round(1.0 / speed, 3))]  # larger scale is slower
    with _slots:
        result = subprocess.run(
            command, input=text.encode("utf-8"), capture_output=True,
            env={**os.environ, "OMP_NUM_THREADS": CPU_THREADS},
        )
    if result.returncode != 0 or not result.stdout:
        error = result.stderr.decode("utf-8", "replace")[:500]
        raise HTTPException(status_code=500, detail=f"piper failed (code {result.returncode}): {error}")
    return result.stdout


@app.post("/v1/audio/speech")
def speech(request: SpeechRequest):
    text = (request.input or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty input")
    return Response(content=synthesize(text, request.speed), media_type="audio/wav")
