FROM node:20-alpine AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY frontend/ ./
ENV VITE_API_URL=
RUN pnpm run build

FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=frontend-build /frontend/dist ./app/static

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python scripts.py load-mock && python scripts.py generate-predictions && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
