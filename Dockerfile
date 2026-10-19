# Reproducible environment for Group 6 (Verifier-Guided Repair).
# Primary execution path is Kaggle (scripts/kaggle_setup.sh); this image mirrors it.
# Size: 16.6 GB on linux/arm64 (Lean toolchain + Mathlib cache), build ~6 min. Needs >= 16 GB RAM per 4 REPL workers.
# Run with an init process so killed REPL children are reaped: docker run --init ... (compose sets init: true).
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PATH="/root/.elan/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl git ca-certificates build-essential python3 python3-pip python3-venv zip unzip \
    && rm -rf /var/lib/apt/lists/*

# Lean toolchain pinned by lean_ws/lean-toolchain (v4.35.0)
RUN curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
    | sh -s -- -y --no-modify-path --default-toolchain none

WORKDIR /workspace
COPY lean_ws/ /workspace/lean_ws/
RUN elan default "$(cat lean_ws/lean-toolchain)" \
    && cd lean_ws && lake exe cache get && lake build repl

COPY requirements.txt requirements-lock.txt /workspace/
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements-lock.txt
ENV PATH="/opt/venv/bin:${PATH}"

COPY . /workspace/
# Default: unit tests (no Lean/API needed). Experiments: see README "Reproduce".
CMD ["python", "-m", "pytest", "tests", "-q"]
