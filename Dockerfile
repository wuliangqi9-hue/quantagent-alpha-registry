FROM node:20-alpine AS web-build

WORKDIR /app/apps/web
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web ./
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV PYTHONPATH=/app/packages/factor-engine:/app/packages/strategy-selector:/app/packages/agent-memory:/app/packages/agent-orchestrator

WORKDIR /app

COPY services/api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY services ./services
COPY packages ./packages
COPY data ./data
COPY --from=web-build /app/apps/web/dist ./apps/web/dist

EXPOSE 8000

CMD ["sh", "-c", "uvicorn services.api.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
