# BeforeImpact AI

**See the risk. Change the outcome.** BeforeImpact is a climate-resilience workspace for
business owners and facility managers. Its signature StormTwin experience replays seeded
weather events across an interactive 3D facility, grounds preparation actions in a reviewed
catalogue, and compares deterministic illustrative exposure scenarios.

## Demo account

- Email: `demo@beforeimpact.ai`
- Password: `Demo123!`

These credentials and the included data are development-only. Seeded weather, flood depths,
warnings, and modeled outcomes are visibly labelled synthetic or illustrative.

## Architecture

- `frontend/`: Next.js, TypeScript, React Three Fiber, MapLibre, Recharts, Zustand
- `backend/`: FastAPI, Pydantic, SQLAlchemy, Alembic, deterministic scenario model
- PostgreSQL-ready via `DATABASE_URL`; SQLite is the zero-configuration demo fallback
- Uploaded plans and generated PDFs are private API resources protected by ownership checks

## Run locally

Requirements: Node 20+, Python 3.9+ (3.12 recommended).

```powershell
Copy-Item .env.example .env
python -m pip install -r backend/requirements.txt
Set-Location backend
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```powershell
Set-Location frontend
npm install
$env:NEXT_PUBLIC_API_URL='http://localhost:8000'
npm run dev
```

Open `http://localhost:3000`. API documentation is at `http://localhost:8000/docs`.

## Verification

```powershell
Set-Location backend
python -m pytest

Set-Location ../frontend
npm run typecheck
npm run build
```

The automated API suite covers authentication, facility access, ordered replay data,
preparation persistence, deterministic prepared/unprepared differences, invalid blueprint
rejection, report generation, and idempotent seeding.

## Two-minute demo path

1. Sign in with the demo account and open GreenVale Greenhouses.
2. Open **StormTwin**, play Storm Céleste, and scrub toward the peak.
3. Select a greenhouse in the scene and inspect its vulnerability record.
4. Generate a preparation plan and complete at least two actions.
5. Save and compare the scenario with no preparation.
6. Switch the facility selector to Riverside Distribution Centre and open its inundation event.
7. In **My Sites**, select Future Logistics Hub to review the seeded synthetic blueprint and markers.

## Model and data limits

The scenario engine is a reproducible educational exposure model (`exposure-1.0`), not a
validated structural, hydrological, catastrophe-loss, safety, or insurance model. Rainfall is
never converted into claimed local flood depth. Flood scenes use an explicit user/demo depth.
No official warning is invented when a provider is unavailable. Proposed-site results are
preliminary screening only and require appropriate professional review.
