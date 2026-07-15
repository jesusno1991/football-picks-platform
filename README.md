# Football Picks Platform

Aplicacion web desde cero para analisis de futbol prepartido, generacion de picks estadisticos y seguimiento de rendimiento.

El enfoque principal son mercados de goles. Corners queda como mercado secundario.

## Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL.
- Frontend: React, TypeScript, Vite, Tailwind CSS, TanStack Query, Recharts.
- Calidad: Pytest, Ruff, Black.
- Deploy: Docker, Docker Compose, Railway.

## Primer arranque local

Backend:

```bash
cd football-picks-platform/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd football-picks-platform/frontend
npm install
npm run dev
```

Docker Compose:

```bash
cd football-picks-platform
docker compose up --build
```

Para pruebas locales sin APIs reales puedes usar `DATA_PROVIDER=mock`, cargar datos desde el panel de administración y recalcular predicciones. En producción no debe usarse mock.

## Endpoints

- `GET /api/health`
- `GET /api/readiness`
- `GET /api/model-health`
- `GET /api/matches?date=YYYY-MM-DD`
- `GET /api/matches/range?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`
- `GET /api/calendar/month?year=YYYY&month=MM`
- `GET /api/matches/{id}`
- `GET /api/matches/{id}/statistics`
- `GET /api/matches/{id}/events`
- `GET /api/matches/{id}/lineups`
- `GET /api/matches/{id}/odds`
- `GET /api/matches/{id}/markets`
- `GET /api/competitions`
- `GET /api/teams/{id}`
- `GET /api/search?q=`
- `GET /api/predictions`
- `GET /api/predictions/export?date=YYYY-MM-DD`
- `GET /api/predictions/{id}`
- `GET /api/statistics/overview`
- `GET /api/statistics/systems`
- `GET /api/statistics/markets`
- `GET /api/statistics/competitions`
- `GET /api/statistics/profit-curve`
- `POST /api/admin/collect`
- `POST /api/admin/generate-predictions`
- `POST /api/admin/verify-results`
- `POST /api/admin/recalculate-statistics`
- `POST /api/admin/import-range`
- `POST /api/admin/sync-day`
- `POST /api/admin/sync-day-deep`
- `POST /api/admin/sync-match-deep`
- `POST /api/admin/rank-markets`
- `POST /api/admin/run-maintenance`

Los endpoints admin requieren cabecera:

```text
X-Admin-Token: <SECRET_KEY>
```

## Reglas actuales

- Solo picks prepartido.
- No se publican picks si faltan menos de 15 minutos para el inicio.
- Las predicciones se calculan por mercado, no solo por partido.
- La cuota debe estar mapeada, validada y ser reciente.
- No se usa una cuota antigua o no verificada para marcar picks publicables.
- Si no hay ventaja estadistica clara, el sistema guarda el candidato como no publicable y no fuerza picks.
- La exportacion diaria excluye partidos de otra fecha local, iniciados, finalizados, cancelados o suspendidos.

## Railway

El despliegue principal usa el `Dockerfile` de la raiz. Ese Dockerfile compila el frontend y lo copia al backend FastAPI para servir una sola aplicacion desde Railway.

Crear:

1. PostgreSQL.
2. Servicio web desde el repositorio raiz.

Variables minimas:

```text
DATABASE_URL=
SECRET_KEY=
DATA_PROVIDER=api_football
API_FOOTBALL_KEY=
RAPIDAPI_KEY=
FLASHSCORE_RAPIDAPI_HOST=flashscore4.p.rapidapi.com
FRONTEND_URL=
BACKEND_URL=
```

Variables recomendadas:

```text
ENVIRONMENT=production
RATE_LIMIT_REQUESTS_PER_MINUTE=240
EXPORT_MAX_ODDS_AGE_HOURS=24
APP_TIMEZONE=Europe/Madrid
```

## Checks antes de publicar

- `pytest backend/tests`
- `python -m compileall backend/app`
- `pnpm --dir frontend run build`
- `GET /api/health`
- `GET /api/readiness`
- Verificar en `/model-health` que no aparece proveedor mock, faltan cuotas recientes o errores de sincronizacion.
