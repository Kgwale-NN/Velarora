FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/react/package*.json ./
RUN npm ci
COPY frontend/react/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPEN_BROWSER=false \
    VELARORA_CLOUD_DEMO=true BIND_HOST=0.0.0.0 PORT=10000 \
    TZ=Africa/Johannesburg OMP_NUM_THREADS=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 tzdata \
    && rm -rf /var/lib/apt/lists/*
COPY requirements-cloud.txt ./
RUN pip install --no-cache-dir -r requirements-cloud.txt
COPY backend/ ./backend/
COPY frontend/assets/ ./frontend/assets/
COPY --from=frontend /build/dist ./frontend/react/dist
COPY run.py ./
RUN mkdir -p data .nicegui && useradd --uid 10001 --create-home velarora \
    && chown -R velarora:velarora /app
USER velarora
EXPOSE 10000
CMD ["python", "run.py"]
