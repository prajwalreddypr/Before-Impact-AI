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

## Resilience Lab

Choose **Try Decision Studio · school example** on the welcome screen for a ready-to-compare school project, then open **Resilience Lab**. For your own project, select a plot, confirm a blueprint, then choose **Explore flood adaptations** or continue from the materials screen.

- Set an adaptation budget, hypothetical water level, extra clearance, and permitted floor raise.
- Compare the lowest-cost, lowest-added-carbon, and greatest-clearance alternatives that meet your constraints. Duplicate winners are combined.
- Switch the 3D view between the original and proposed design. The yellow marker represents critical equipment at its stated elevation; its location is schematic.
- Challenge a proposal with a higher water level, or halve the budget and compare again. Impossible requests report the limiting constraint rather than applying a failing option.
- Inspect every quantity, unit allowance, and clearance calculation. Edit the demo cost/carbon assumptions as needed.
- Apply a design to save its elevations to the simulator and include the comparison in a planning report. Projects, selected plot details, material choices, and saved comparisons can be reopened.

The lab searches a finite catalogue in 0.1 m increments: two solid-platform mixes, up to 3 m of floor raise, and up to 1.5 m of additional equipment mounting. It checks vertical clearance using user inputs. Prices and carbon factors are illustrative allowances, not supplier quotes or validated lifecycle data. It does not simulate flood dynamics, structural response, or evacuation. An equipment-only target can leave the floor exposed. No API key is needed for this comparison; blueprint AI remains optional.

Implementation and demo details: [Resilience Lab](docs/RESILIENCE_LAB.md).

## Decision Studio: five connected features

- **Brief copilot:** turn a plain-language brief into reviewed constraints; optional AI, with a key-free local parser.
- **Official site evidence:** attach real French address and municipality hazard records from IGN and Géorisques, with scope, timestamps and links.
- **Design library:** preserve named alternatives and their original assumptions; compare and reopen without losing earlier work.
- **Stress grid:** challenge one fixed design across 24 water-and-cost scenarios, show exact limiting constraints, and retain the result.
- **Decision story:** present five scenes and download a sourced decision brief covering alternatives, calculations and remaining verification needs.

Start with **Try Decision Studio · school example**. [Workflow, implementation and demo script](docs/DECISION_STUDIO.md).

## Blueprint understanding

After a PDF, PNG, or JPEG plan is uploaded, SustainBuild scans it into a strict structured result: footprint dimensions, floor count, room/zone labels, approximate areas, confidence, assumptions, and uncertainties. The user must review or correct those findings before the conceptual 3D model is generated.

Set `OPENAI_API_KEY` to enable multimodal analysis through the OpenAI Responses API. `OPENAI_BLUEPRINT_MODEL` controls the vision-capable model and defaults to `gpt-6-astra`. Without a key—or if analysis is unavailable—the UI clearly identifies the result as **Demo Extraction** and uses a deterministic building-type profile instead of claiming that AI inspected the drawing.

## Run locally

Requirements: Node 20+, Python 3.10+ (3.12 recommended).

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
npm test
npm run build
```

## Limits

Scenario graphics are conceptual exposure illustrations—not validated structural, hydrological, thermal, fire-spread, seismic-response, code-compliance, or lifecycle assessments. SustainBuild does not replace architects, engineers, environmental consultants, permitting authorities, or official hazard assessments.
