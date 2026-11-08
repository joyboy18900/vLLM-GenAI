"""Speech to text service.

It offers the OpenAI transcription route on top of faster-whisper. It runs on the CPU
(int8), so all GPU memory stays with vLLM. The model weights download on first use
into HF_HOME, which is a mounted volume.

All settings come from STT_* environment variables.
"""
import os
import tempfile
import time

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from faster_whisper import WhisperModel
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

MODEL = os.getenv("STT_MODEL", "small")
DEVICE = os.getenv("STT_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("STT_COMPUTE_TYPE", "int8")
CPU_THREADS = int(os.getenv("STT_CPU_THREADS", "0"))  # 0: the library chooses

# Greedy decoding (beam 1) is much faster on the CPU. It costs little accuracy on
# short utterances from one speaker.
BEAM_SIZE = int(os.getenv("STT_BEAM_SIZE", "1"))
# Voice mode is English first. A fixed language skips the language detection step.
# An empty value turns detection on. A `language` form field overrides this value.
LANGUAGE = os.getenv("STT_LANGUAGE", "en") or None
# Each utterance is separate. Set to 1 only to carry the decoder state to the next one.
CARRY_CONTEXT = os.getenv("STT_CARRY_CONTEXT", "0") == "1"

model = WhisperModel(MODEL, device=DEVICE, compute_type=COMPUTE_TYPE, cpu_threads=CPU_THREADS)

REQUESTS = Counter("stt_requests_total", "Transcription requests", ["status"])
LATENCY = Histogram(
    "stt_request_duration_seconds", "Transcription request duration",
    buckets=(0.1, 0.25, 0.5, 1, 2, 4, 8, 16, 32),
)

app = FastAPI(title="stt")


@app.middleware("http")
async def measure(request: Request, call_next):
    if request.url.path != "/v1/audio/transcriptions":
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
    return {
        "status": "ok", "model": MODEL, "device": DEVICE, "compute_type": COMPUTE_TYPE,
        "beam_size": BEAM_SIZE, "language": LANGUAGE or "auto",
    }


# A plain `def` route runs in a worker thread. A long transcription then does not block
# /health, so the liveness probe keeps working.
@app.post("/v1/audio/transcriptions")
def transcribe(
    file: UploadFile = File(...),
    model_name: str = Form(default=None, alias="model"),  # accepted and ignored: one model is loaded
    language: str = Form(default=None),
    prompt: str = Form(default=None),
    response_format: str = Form(default="json"),
    temperature: float = Form(default=0.0),
):
    suffix = os.path.splitext(file.filename or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix) as upload:
        upload.write(file.file.read())
        upload.flush()
        segments, info = model.transcribe(
            upload.name,
            language=language or LANGUAGE,
            initial_prompt=prompt,
            temperature=temperature,
            beam_size=BEAM_SIZE,
            condition_on_previous_text=CARRY_CONTEXT,
            vad_filter=True,
        )
        text = "".join(segment.text for segment in segments).strip()

    if response_format in ("text", "srt", "vtt"):
        return PlainTextResponse(text)
    return JSONResponse({"text": text, "language": info.language})
