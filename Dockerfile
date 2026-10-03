# Public, replay-only LabForge demo (Hugging Face Docker Space, or any container host).
# Builds the game client, then serves it with the API from one uvicorn process on port 7860.
# Live agent runs are off (LABFORGE_REPLAY_ONLY=1); no API keys are baked in or needed.

FROM node:22-slim AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json frontend/
RUN cd frontend && npm ci
COPY examples examples
COPY schemas schemas
COPY frontend frontend
RUN cd frontend && VITE_API= npx vite build

FROM python:3.11-slim
RUN useradd -m -u 1000 user
WORKDIR /home/user/app
COPY --chown=user backend backend
COPY --chown=user schemas schemas
COPY --chown=user examples examples
RUN pip install --no-cache-dir -e backend
COPY --chown=user --from=frontend /app/frontend/dist frontend/dist
USER user
ENV LABFORGE_REPLAY_ONLY=1 \
    LABFORGE_STATIC_DIR=/home/user/app/frontend/dist \
    LABFORGE_SIM_BACKEND=serial \
    HOME=/home/user
EXPOSE 7860
CMD ["uvicorn", "labforge.gateway:app", "--host", "0.0.0.0", "--port", "7860", "--app-dir", "backend"]
