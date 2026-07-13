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
python scripts.py load-mock
python scripts.py generate-predictions
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

## Endpoints

- `GET /api/matches`
- `GET /api/matches/{id}`
- `GET /api/competitions`
- `GET /api/teams/{id}`
- `GET /api/predictions`
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

Los endpoints admin requieren cabecera:

```text
X-Admin-Token: <SECRET_KEY>
```

## Reglas actuales

- Solo picks prepartido.
- No se publican picks si faltan menos de 15 minutos para el inicio.
- Se exige muestra minima de 10 partidos combinados.
- La cuota disponible debe superar la cuota justa.
- EV positivo y por encima del minimo del sistema.
- Sistemas activos principales: `GOALS_OVER15_V1`, `GOALS_OVER25_V1`, `GOALS_OVER35_V1` y `BTTS_V1`.
- Sistema secundario activo: `CORNERS_OVER_95`.
- Si no hay ventaja estadistica clara, el sistema guarda `NO BET` y no fuerza picks.

## Railway

Crear servicios separados:

1. PostgreSQL.
2. Backend desde `backend/Dockerfile`.
3. Frontend desde `frontend/Dockerfile`.

Variables minimas:

```text
DATABASE_URL=
SECRET_KEY=
DATA_PROVIDER=mock
FRONTEND_URL=
BACKEND_URL=
VITE_API_URL=
```

## Notas

El proveedor actual es mock y esta desacoplado mediante `FootballDataProvider`. La integracion real se anade creando una clase nueva que implemente esa interfaz.
