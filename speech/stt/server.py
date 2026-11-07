"""STT server - OpenAI-compatible /v1/audio/transcriptions backed by faster-whisper.

Runs on CPU only (compute_type int8), so the GPU stays free for vLLM. Model
weights download on first use into HF_HOME, which is a mounted volume.
"""
import os
import tempfile

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from faster_whisper import WhisperModel

MODEL_SIZE = os.getenv("WHISPER_MODEL", "small.en")
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
CPU_THREADS = int(os.getenv("WHISPER_CPU_THREADS", "0"))  # 0 = let ctranslate2 decide

# Greedy decoding (beam 1) is much faster on CPU and costs little accuracy on
# short single-speaker utterances.
BEAM_SIZE = int(os.getenv("WHISPER_BEAM_SIZE", "1"))
# The voice stack is English first. A fixed language skips the detection pass.
# An empty value keeps auto-detect. A per-request `language` field overrides it.
DEFAULT_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "en") or None
# Voice utterances are independent. Do not carry decoder state between them.
CONDITION_ON_PREV = os.getenv("WHISPER_CONDITION_ON_PREV", "0") == "1"

whisper = WhisperModel(
    MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE, cpu_threads=CPU_THREADS
)

app = FastAPI(title="stt-faster-whisper")


@app.get("/health")
def health():
    return {
        "status": "ok", "model": MODEL_SIZE, "device": DEVICE,
        "compute_type": COMPUTE_TYPE, "beam_size": BEAM_SIZE,
        "language": DEFAULT_LANGUAGE or "auto",
    }


@app.post("/v1/audio/transcriptions")
async def transcriptions(
    file: UploadFile = File(...),
    model: str = Form(default=None),  # accepted and ignored (one model is loaded)
    language: str = Form(default=None),
    prompt: str = Form(default=None),
    response_format: str = Form(default="json"),
    temperature: float = Form(default=0.0),
):
    suffix = os.path.splitext(file.filename or "audio.wav")[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        path = tmp.name
    try:
        segments, info = whisper.transcribe(
            path,
            language=language or DEFAULT_LANGUAGE,
            initial_prompt=prompt,
            temperature=temperature,
            beam_size=BEAM_SIZE,
            condition_on_previous_text=CONDITION_ON_PREV,
            vad_filter=True,
        )
        text = "".join(seg.text for seg in segments).strip()
    finally:
        os.unlink(path)

    if response_format in ("text", "srt", "vtt"):
        return PlainTextResponse(text)
    return JSONResponse({"text": text, "language": info.language})
