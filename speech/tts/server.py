"""TTS server - OpenAI-compatible /v1/audio/speech backed by Piper.

Piper runs on CPU only, so it takes no VRAM from vLLM. Each request runs the
Piper CLI, which writes a WAV file to stdout.
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

VOICE_PATH = os.getenv("PIPER_VOICE_PATH", "/voices/en_US-lessac-medium.onnx")
# Open WebUI splits a long reply into many sentence requests. Piper adds its own
# trailing silence to each one. Set it to 0 to avoid audible gaps.
SENTENCE_SILENCE = os.getenv("PIPER_SENTENCE_SILENCE", "0.0")
# Open WebUI sends many requests in parallel. Each one starts a Piper process
# that uses a lot of memory, so run them one at a time by default.
MAX_CONCURRENCY = int(os.getenv("PIPER_MAX_CONCURRENCY", "1"))
_slot = threading.Semaphore(MAX_CONCURRENCY)

REQUESTS = Counter("tts_requests_total", "Speech requests", ["status"])
LATENCY = Histogram(
    "tts_request_duration_seconds", "Speech request duration",
    buckets=(0.1, 0.25, 0.5, 1, 2, 4, 8, 16),
)

app = FastAPI(title="tts-piper")


@app.middleware("http")
async def measure(request: Request, call_next):
    if request.url.path != "/v1/audio/speech":
        return await call_next(request)
    start = time.perf_counter()
    status = "500"
    try:
        response = await call_next(request)
        status = str(response.status_code)
        return response
    finally:
        REQUESTS.labels(status).inc()
        LATENCY.observe(time.perf_counter() - start)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


class SpeechRequest(BaseModel):
    input: str
    model: str | None = None  # accepted and ignored
    voice: str | None = None  # accepted and ignored (one voice is loaded)
    response_format: str | None = "wav"  # Piper makes WAV only
    speed: float | None = None


@app.get("/health")
def health():
    return {"status": "ok", "voice": os.path.basename(VOICE_PATH)}


@app.post("/v1/audio/speech")
def speech(req: SpeechRequest):
    text = (req.input or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty input")

    cmd = [
        sys.executable, "-m", "piper", "--model", VOICE_PATH,
        "--sentence-silence", SENTENCE_SILENCE, "--output-file", "-",
    ]
    if req.speed and req.speed > 0:
        cmd += ["--length-scale", str(round(1.0 / req.speed, 3))]

    with _slot:
        proc = subprocess.run(
            cmd, input=text.encode("utf-8"), capture_output=True,
            env={**os.environ, "OMP_NUM_THREADS": os.getenv("PIPER_OMP_THREADS", "2")},
        )
    if proc.returncode != 0 or not proc.stdout:
        raise HTTPException(
            status_code=500,
            detail=f"piper failed (rc={proc.returncode}): {proc.stderr.decode('utf-8', 'replace')[:500]}",
        )
    return Response(content=proc.stdout, media_type="audio/wav")
