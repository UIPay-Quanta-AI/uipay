FROM python:3.12-slim

WORKDIR /app

# ffmpeg/libsndfile1: audio decode/transcode for the voice pipeline.
# libgomp1: OpenMP runtime paddlepaddle and numpy's BLAS backend need.
# libgl1/libglib2.0-0: paddleocr pulls in opencv, which dlopens libGL even
# in headless mode - without these, import fails with
# "ImportError: libGL.so.1: cannot open shared object file".
# git: huggingface_hub occasionally needs it to resolve model repos.
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY README.md ./

# Install the CPU-only torch wheel first and pin it in place. Plain
# `pip install torch` (what `pip install -e .` would otherwise trigger)
# resolves the default PyPI build, which bundles CUDA and runs 2-3GB+ -
# wasted size and build time on a CPU-only host like this one.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -e .

COPY app/ ./app/

# Railway injects $PORT at container start and routes to whatever the app
# actually binds - it ignores EXPOSE and won't substitute a variable into a
# JSON-array CMD, so this has to be shell form for $PORT to expand. The
# :-8000 fallback is only for running this image somewhere that doesn't set
# PORT (a local `docker run`, say).
EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
