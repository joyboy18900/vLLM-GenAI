# Environment to compare Thai TTS candidates on the CPU.
# The FastThaiG2P package comes from GitHub (awslabs/FastThaiG2P, Apache-2.0), pinned to a tag.
# Its model (about 326 MB) downloads from the GitHub release v0.3.0 on the first run.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir piper-tts==1.8.0 onnxruntime numpy \
    "fastthaig2p[tts] @ git+https://github.com/awslabs/FastThaiG2P.git@v0.3.0"
WORKDIR /work
COPY compare.py sentences.json ./
ENTRYPOINT ["python", "compare.py"]
