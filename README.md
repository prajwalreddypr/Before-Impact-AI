# SustainBuild AI

**Before You Build, Understand the Impact.** SustainBuild is a climate-resilient and sustainable construction-planning workspace. It helps communities, architects, and developers compare candidate sites, confirm blueprint geometry, test conceptual hazards and adaptations, and understand sustainability trade-offs before construction begins.

## Demo account

- Email: `demo@beforeimpact.ai` (legacy internal demo credential retained for existing local data)
- Password: `Demo123!`

The included candidate plots, climate profiles, planning constraints, pollution values, and hazard contexts are fictional hackathon demo data. They are visibly labelled synthetic and are not land listings, official measurements, permissions, or engineering advice.

## Architecture

- `frontend/`: Next.js, TypeScript, React Three Fiber, MapLibre, Recharts, Zustand
- `backend/`: FastAPI, Pydantic, SQLAlchemy, Alembic, ReportLab
- PostgreSQL-ready via `DATABASE_URL`; SQLite is the zero-configuration demo fallback
- Uploaded plans and generated PDFs are private API resources protected by ownership checks

## Blueprint understanding

After a PDF, PNG, or JPEG plan is uploaded, SustainBuild scans it into a strict structured result: footprint dimensions, floor count, room/zone labels, approximate areas, confidence, assumptions, and uncertainties. The user must review or correct those findings before the conceptual 3D model is generated.

Set `OPENAI_API_KEY` to enable multimodal analysis through the OpenAI Responses API. `OPENAI_BLUEPRINT_MODEL` controls the vision-capable model and defaults to `gpt-6-astra`. Without a key—or if analysis is unavailable—the UI clearly identifies the result as **Demo Extraction** and uses a deterministic building-type profile instead of claiming that AI inspected the drawing.

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

## Primary school demo

1. Sign in and create the climate-resilient community school project.
2. Find and select two or three fictional Japanese candidate plots.
3. Review climate, planning, and environmental Site Intelligence.
4. Load the sample school plan, confirm dimensions, and generate the conceptual 3D school.
5. Run a 0.8 m hypothetical flood scenario, raise the finished floor to 1.0 m, and compare before/after intersection.
6. Switch sites without changing the building geometry.
7. Calculate rainwater capture and embodied carbon, then export the planning report.

## Verification

```powershell
Set-Location backend
python -m pytest

Set-Location ../frontend
npm run typecheck
npm run build
```

## Limits

Scenario graphics are conceptual exposure illustrations—not validated structural, hydrological, thermal, fire-spread, seismic-response, code-compliance, or lifecycle assessments. SustainBuild does not replace architects, engineers, environmental consultants, permitting authorities, or official hazard assessments.
