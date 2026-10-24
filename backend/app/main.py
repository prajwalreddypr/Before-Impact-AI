import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import jwt
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import (Asset, Blueprint, BlueprintMarker, Facility, PlanItem,
                     PreparationAction, PreparationPlan, Report, Scenario,
                     ScenarioResult, User, Warning, WeatherEvent, WeatherReading)
from .scenario import calculate_exposure
from .seed import DEMO_EMAIL, password_hash, seed_demo


app = FastAPI(title="BeforeImpact AI", version="1.0.0", description="Climate resilience replay and preparation API")
origins = [x.strip() for x in os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
SECRET_KEY = os.getenv("SECRET_KEY", "beforeimpact-local-demo-secret")
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

SITE_PRESETS = [
    {"id":"tokyo-bay","name":"Tokyo Bay","region":"Kanto","latitude":35.58,"longitude":139.78,"annual_rainfall_mm":1598,"grid_carbon_gco2_kwh":438,"rainwater_score":82,"hazards":{"wind":68,"rain":76,"flood":72,"heat":64,"wildfire":24,"drought":31}},
    {"id":"osaka-coast","name":"Osaka Coast","region":"Kansai","latitude":34.64,"longitude":135.40,"annual_rainfall_mm":1338,"grid_carbon_gco2_kwh":412,"rainwater_score":74,"hazards":{"wind":63,"rain":69,"flood":70,"heat":71,"wildfire":29,"drought":38}},
    {"id":"sendai-port","name":"Sendai Port","region":"Tohoku","latitude":38.27,"longitude":141.02,"annual_rainfall_mm":1254,"grid_carbon_gco2_kwh":401,"rainwater_score":68,"hazards":{"wind":72,"rain":61,"flood":66,"heat":42,"wildfire":28,"drought":25}},
    {"id":"nagoya-east","name":"Nagoya East","region":"Chubu","latitude":35.14,"longitude":137.05,"annual_rainfall_mm":1578,"grid_carbon_gco2_kwh":420,"rainwater_score":80,"hazards":{"wind":65,"rain":72,"flood":48,"heat":68,"wildfire":34,"drought":39}},
    {"id":"sapporo-north","name":"Sapporo North","region":"Hokkaido","latitude":43.12,"longitude":141.35,"annual_rainfall_mm":1146,"grid_carbon_gco2_kwh":465,"rainwater_score":62,"hazards":{"wind":58,"rain":42,"flood":35,"heat":28,"wildfire":32,"drought":22}},
    {"id":"fukuoka-hakata","name":"Fukuoka Hakata","region":"Kyushu","latitude":33.59,"longitude":130.45,"annual_rainfall_mm":1687,"grid_carbon_gco2_kwh":451,"rainwater_score":86,"hazards":{"wind":74,"rain":82,"flood":59,"heat":73,"wildfire":36,"drought":42}},
]


@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    seed_demo()


def as_dict(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def token_for(user):
    return jwt.encode({"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(hours=12)}, SECRET_KEY, algorithm="HS256")


def current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentication required")
    try:
        payload = jwt.decode(authorization[7:], SECRET_KEY, algorithms=["HS256"])
        user = db.get(User, int(payload["sub"]))
    except Exception:
        user = None
    if not user:
        raise HTTPException(401, "Invalid or expired session")
    return user


def owned_facility(db, user, facility_id):
    facility = db.get(Facility, facility_id)
    if not facility or facility.owner_user_id != user.id:
        raise HTTPException(404, "Facility not found")
    return facility


class LoginIn(BaseModel):
    email: str
    password: str


class FacilityIn(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    facility_type: str
    industry: str = "Other"
    country: str
    address_label: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = "UTC"
    currency: str = "EUR"
    status: str = "existing"


class FacilityPatch(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    address_label: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: Optional[str] = None


class AssetIn(BaseModel):
    name: str
    asset_type: str
    description: str = ""
    value_amount: float = Field(default=0, ge=0)
    currency: str = "EUR"
    relative_x: float = 0
    relative_y: float = 0
    relative_z: float = 0
    dimensions_json: Dict[str, Any] = {}
    vulnerability_profile_json: Dict[str, Any] = {}
    preparedness_status: str = "unreviewed"


class AssetPatch(BaseModel):
    name: Optional[str] = None
    value_amount: Optional[float] = Field(default=None, ge=0)
    preparedness_status: Optional[str] = None
    vulnerability_profile_json: Optional[Dict[str, Any]] = None


class PlanItemPatch(BaseModel):
    status: Optional[str] = None
    user_notes: str = ""
    assignee_name: Optional[str] = None


class ScenarioIn(BaseModel):
    facility_id: int
    weather_event_id: int
    name: str
    scenario_type: str = "prepared"
    selected_action_ids: List[int] = []


class CompareIn(BaseModel):
    scenario_a_id: int
    scenario_b_id: int


class MarkerIn(BaseModel):
    normalized_x: float = Field(ge=0, le=1)
    normalized_y: float = Field(ge=0, le=1)
    label: str
    marker_type: str = "asset"
    asset_id: Optional[int] = None


class ReportIn(BaseModel):
    facility_id: int
    scenario_id: Optional[int] = None
    report_type: str = "scenario_summary"
    title: str = "Climate resilience scenario report"


class SiteEvaluationIn(BaseModel):
    preset_id: str
    facility_type: str
    roof_area_m2: float = Field(default=2400, ge=50, le=200000)
    simulations: Dict[str, int] = {}


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "BeforeImpact AI", "model_version": "exposure-1.0"}


@app.get("/api/site-presets")
def site_presets(user=Depends(current_user)):
    return {"locations": SITE_PRESETS, "synthetic": True,
            "notice": "Synthetic planning dataset for product demonstration; validate with authoritative local sources."}


@app.post("/api/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not secrets.compare_digest(user.password_hash, password_hash(body.password)):
        raise HTTPException(401, "Incorrect email or password")
    return {"access_token": token_for(user), "token_type": "bearer", "user": as_dict(user)}


@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    return as_dict(user)


@app.post("/api/auth/logout")
def logout(user=Depends(current_user)):
    return {"ok": True}


@app.get("/api/facilities")
def facilities(db: Session = Depends(get_db), user=Depends(current_user)):
    return [as_dict(x) for x in db.scalars(select(Facility).where(Facility.owner_user_id == user.id).order_by(Facility.id))]


@app.post("/api/facilities")
def create_facility(body: FacilityIn, db: Session = Depends(get_db), user=Depends(current_user)):
    row = Facility(owner_user_id=user.id, **body.model_dump()); db.add(row); db.commit(); db.refresh(row)
    return as_dict(row)


@app.get("/api/facilities/{facility_id}")
def facility_detail(facility_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    facility = owned_facility(db, user, facility_id)
    data = as_dict(facility)
    data["assets"] = [as_dict(x) for x in db.scalars(select(Asset).where(Asset.facility_id == facility_id))]
    return data


@app.patch("/api/facilities/{facility_id}")
def update_facility(facility_id: int, body: FacilityPatch, db: Session = Depends(get_db), user=Depends(current_user)):
    row = owned_facility(db, user, facility_id)
    for key, value in body.model_dump(exclude_none=True).items(): setattr(row, key, value)
    db.commit(); db.refresh(row); return as_dict(row)


@app.delete("/api/facilities/{facility_id}")
def remove_facility(facility_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = owned_facility(db, user, facility_id); db.delete(row); db.commit(); return {"deleted": True}


@app.get("/api/facilities/{facility_id}/assets")
def assets(facility_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    owned_facility(db, user, facility_id)
    return [as_dict(x) for x in db.scalars(select(Asset).where(Asset.facility_id == facility_id).order_by(Asset.id))]


@app.post("/api/facilities/{facility_id}/assets")
def create_asset(facility_id: int, body: AssetIn, db: Session = Depends(get_db), user=Depends(current_user)):
    owned_facility(db, user, facility_id); row = Asset(facility_id=facility_id, **body.model_dump()); db.add(row); db.commit(); db.refresh(row); return as_dict(row)


@app.patch("/api/assets/{asset_id}")
def update_asset(asset_id: int, body: AssetPatch, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(Asset, asset_id)
    if not row: raise HTTPException(404, "Asset not found")
    owned_facility(db, user, row.facility_id)
    for key, value in body.model_dump(exclude_none=True).items(): setattr(row, key, value)
    db.commit(); db.refresh(row); return as_dict(row)


@app.delete("/api/assets/{asset_id}")
def remove_asset(asset_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(Asset, asset_id)
    if not row: raise HTTPException(404, "Asset not found")
    owned_facility(db, user, row.facility_id); db.delete(row); db.commit(); return {"deleted": True}


@app.get("/api/facilities/{facility_id}/events")
def events(facility_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    owned_facility(db, user, facility_id)
    return [as_dict(x) for x in db.scalars(select(WeatherEvent).where(WeatherEvent.facility_id == facility_id).order_by(WeatherEvent.start_at))]


@app.get("/api/events/{event_id}")
def event_detail(event_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(WeatherEvent, event_id)
    if not row: raise HTTPException(404, "Event not found")
    owned_facility(db, user, row.facility_id); return as_dict(row)


@app.get("/api/events/{event_id}/timeline")
def timeline(event_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    event = db.get(WeatherEvent, event_id)
    if not event: raise HTTPException(404, "Event not found")
    owned_facility(db, user, event.facility_id)
    readings = list(db.scalars(select(WeatherReading).where(WeatherReading.weather_event_id == event_id).order_by(WeatherReading.timestamp)))
    return {"event": as_dict(event), "readings": [as_dict(x) for x in readings], "source": {"provider": event.provider, "synthetic": event.is_synthetic, "url": event.source_url}}


@app.get("/api/facilities/{facility_id}/weather/history")
def history(facility_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    return events(facility_id, db, user)


@app.get("/api/facilities/{facility_id}/weather/current")
def current_weather(facility_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    owned_facility(db, user, facility_id)
    event = db.scalar(select(WeatherEvent).where(WeatherEvent.facility_id == facility_id).order_by(WeatherEvent.id))
    if not event: return {"available": False, "message": "No local current-weather feed configured"}
    reading = db.scalar(select(WeatherReading).where(WeatherReading.weather_event_id == event.id).order_by(WeatherReading.timestamp))
    return {"available": True, "data_type": "synthetic_demo", "reading": as_dict(reading), "provider": event.provider}


@app.get("/api/facilities/{facility_id}/weather/forecast")
def forecast(facility_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    owned_facility(db, user, facility_id)
    return {"available": False, "message": "Live forecast unavailable; historical and what-if scenarios remain available.", "provider": "Open-Meteo adapter ready"}


@app.get("/api/facilities/{facility_id}/warnings")
def warnings(facility_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    owned_facility(db, user, facility_id)
    rows = list(db.scalars(select(Warning).where(Warning.facility_id == facility_id).order_by(Warning.id)))
    return {"warnings": [warning_payload(x, db) for x in rows], "official_feed": False,
            "message": "Synthetic demonstration signals; no official alert has been fabricated."}


def warning_payload(row, db):
    data = as_dict(row)
    facility = db.get(Facility, row.facility_id)
    event = db.get(WeatherEvent, row.weather_event_id)
    data["facility_name"] = facility.name
    data["country"] = facility.country
    data["event_name"] = event.name
    return data


@app.get("/api/warnings")
def portfolio_warnings(db: Session = Depends(get_db), user=Depends(current_user)):
    rows = list(db.scalars(select(Warning).join(Facility).where(Facility.owner_user_id == user.id).order_by(Warning.id)))
    return {"warnings": [warning_payload(x, db) for x in rows], "official_feed": False,
            "message": "Portfolio climate signals from synthetic demonstration events."}


@app.post("/api/events/{event_id}/generate-plan")
def generate_plan(event_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    event = db.get(WeatherEvent, event_id)
    if not event: raise HTTPException(404, "Event not found")
    owned_facility(db, user, event.facility_id)
    plan = PreparationPlan(facility_id=event.facility_id, weather_event_id=event.id, generated_by="deterministic_fallback",
                           summary=f"Prioritised {event.hazard_type} preparation from the reviewed demo catalogue.")
    db.add(plan); db.flush()
    actions = list(db.scalars(select(PreparationAction).where(PreparationAction.hazard_type == event.hazard_type).order_by(PreparationAction.id).limit(6)))
    for action in actions: db.add(PlanItem(plan_id=plan.id, action_id=action.id, status="suggested"))
    db.commit(); return plan_detail(plan.id, db, user)


@app.get("/api/plans/{plan_id}")
def plan_detail(plan_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    plan = db.get(PreparationPlan, plan_id)
    if not plan: raise HTTPException(404, "Plan not found")
    owned_facility(db, user, plan.facility_id)
    items = []
    for item in db.scalars(select(PlanItem).where(PlanItem.plan_id == plan.id)):
        action = db.get(PreparationAction, item.action_id); item_data = as_dict(item); item_data["action"] = as_dict(action); items.append(item_data)
    data = as_dict(plan); data["items"] = items; return data


@app.patch("/api/plans/{plan_id}/items/{item_id}")
def update_plan_item(plan_id: int, item_id: int, body: PlanItemPatch, db: Session = Depends(get_db), user=Depends(current_user)):
    plan = db.get(PreparationPlan, plan_id)
    if not plan: raise HTTPException(404, "Plan not found")
    owned_facility(db, user, plan.facility_id)
    item = db.get(PlanItem, item_id)
    if not item or item.plan_id != plan_id: raise HTTPException(404, "Plan item not found")
    if body.status is not None:
        if body.status not in ("suggested", "planned", "completed", "not_applicable"): raise HTTPException(422, "Invalid status")
        item.status = body.status
        item.completion_timestamp = datetime.now(timezone.utc) if body.status == "completed" else None
    if body.assignee_name is not None:
        item.assignee_name = body.assignee_name[:120]
    item.user_notes = body.user_notes
    db.commit(); return as_dict(item)


def scenario_payload(row, db):
    data = as_dict(row); result = db.scalar(select(ScenarioResult).where(ScenarioResult.scenario_id == row.id)); data["result"] = as_dict(result)["results_json"] if result else None; return data


@app.post("/api/scenarios")
def create_scenario(body: ScenarioIn, db: Session = Depends(get_db), user=Depends(current_user)):
    owned_facility(db, user, body.facility_id)
    event = db.get(WeatherEvent, body.weather_event_id)
    if not event or event.facility_id != body.facility_id: raise HTTPException(422, "Event does not belong to facility")
    row = Scenario(facility_id=body.facility_id, weather_event_id=body.weather_event_id, name=body.name,
                   scenario_type=body.scenario_type, assumptions_json={"selected_action_ids": body.selected_action_ids})
    db.add(row); db.flush(); db.add(ScenarioResult(scenario_id=row.id, results_json=calculate_exposure(list(db.scalars(select(Asset).where(Asset.facility_id == body.facility_id))), event, body.selected_action_ids)))
    db.commit(); return scenario_payload(row, db)


@app.get("/api/scenarios/{scenario_id}")
def get_scenario(scenario_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(Scenario, scenario_id)
    if not row: raise HTTPException(404, "Scenario not found")
    owned_facility(db, user, row.facility_id); return scenario_payload(row, db)


@app.post("/api/scenarios/{scenario_id}/calculate")
def recalculate(scenario_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(Scenario, scenario_id)
    if not row: raise HTTPException(404, "Scenario not found")
    owned_facility(db, user, row.facility_id); event = db.get(WeatherEvent, row.weather_event_id)
    values = calculate_exposure(list(db.scalars(select(Asset).where(Asset.facility_id == row.facility_id))), event, row.assumptions_json.get("selected_action_ids", []))
    result = db.scalar(select(ScenarioResult).where(ScenarioResult.scenario_id == row.id))
    if result: result.results_json = values; result.calculated_at = datetime.now(timezone.utc)
    else: db.add(ScenarioResult(scenario_id=row.id, results_json=values))
    db.commit(); return values


@app.post("/api/scenarios/compare")
def compare(body: CompareIn, db: Session = Depends(get_db), user=Depends(current_user)):
    a, b = db.get(Scenario, body.scenario_a_id), db.get(Scenario, body.scenario_b_id)
    if not a or not b: raise HTTPException(404, "Scenario not found")
    owned_facility(db, user, a.facility_id); owned_facility(db, user, b.facility_id)
    ra, rb = scenario_payload(a, db)["result"], scenario_payload(b, db)["result"]
    return {"scenario_a": scenario_payload(a, db), "scenario_b": scenario_payload(b, db),
            "difference": {"exposure_points": ra["exposure_score"] - rb["exposure_score"], "loss_range_reduction": [ra["potential_loss_range"][0] - rb["potential_loss_range"][0], ra["potential_loss_range"][1] - rb["potential_loss_range"][1]]},
            "explanation": "The change is produced only by the selected action modifiers under the same illustrative hazard assumptions."}


@app.get("/api/facilities/{facility_id}/scenarios")
def facility_scenarios(facility_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    owned_facility(db, user, facility_id); return [scenario_payload(x, db) for x in db.scalars(select(Scenario).where(Scenario.facility_id == facility_id).order_by(Scenario.id.desc()))]


@app.post("/api/facilities/{facility_id}/blueprints")
async def upload_blueprint(facility_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(current_user)):
    owned_facility(db, user, facility_id)
    allowed = {"application/pdf": ".pdf", "image/png": ".png", "image/jpeg": ".jpg"}
    if file.content_type not in allowed: raise HTTPException(415, "Only PDF, PNG, and JPEG plans are supported")
    content = await file.read(8 * 1024 * 1024 + 1)
    if len(content) > 8 * 1024 * 1024: raise HTTPException(413, "Plan exceeds the 8 MB upload limit")
    safe_name = hashlib.sha256(content).hexdigest()[:18] + allowed[file.content_type]
    path = UPLOAD_DIR / safe_name; path.write_bytes(content)
    row = Blueprint(facility_id=facility_id, filename=Path(file.filename or safe_name).name, storage_path=str(path), mime_type=file.content_type,
                    processing_status="ready" if file.content_type != "application/pdf" else "manual_review", extracted_data_json={"confidence": "not_assessed"})
    db.add(row); db.commit(); db.refresh(row); return as_dict(row)


@app.get("/api/facilities/{facility_id}/blueprints")
def facility_blueprints(facility_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    owned_facility(db, user, facility_id)
    return [as_dict(x) for x in db.scalars(select(Blueprint).where(Blueprint.facility_id == facility_id).order_by(Blueprint.id.desc()))]


@app.post("/api/facilities/{facility_id}/blueprints/demo")
def use_demo_blueprint(facility_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    owned_facility(db, user, facility_id)
    source = db.scalar(select(Blueprint).where(Blueprint.mime_type == "image/svg+xml").order_by(Blueprint.id))
    if not source or not Path(source.storage_path).exists():
        raise HTTPException(404, "Demo plan is unavailable")
    row = Blueprint(facility_id=facility_id, filename="concept-factory-plan.svg", storage_path=source.storage_path,
                    mime_type="image/svg+xml", processing_status="ready", extracted_data_json={"synthetic": True})
    db.add(row); db.commit(); db.refresh(row)
    return as_dict(row)


@app.get("/api/blueprints/{blueprint_id}")
def blueprint(blueprint_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(Blueprint, blueprint_id)
    if not row: raise HTTPException(404, "Blueprint not found")
    owned_facility(db, user, row.facility_id); data = as_dict(row); data["markers"] = [as_dict(x) for x in db.scalars(select(BlueprintMarker).where(BlueprintMarker.blueprint_id == row.id))]; return data


@app.get("/api/blueprints/{blueprint_id}/preview")
def blueprint_preview(blueprint_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(Blueprint, blueprint_id)
    if not row: raise HTTPException(404, "Blueprint not found")
    owned_facility(db, user, row.facility_id); return FileResponse(row.storage_path, media_type=row.mime_type)


@app.post("/api/blueprints/{blueprint_id}/generate-model")
def generate_concept_model(blueprint_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(Blueprint, blueprint_id)
    if not row: raise HTTPException(404, "Blueprint not found")
    owned_facility(db, user, row.facility_id)
    markers = list(db.scalars(select(BlueprintMarker).where(BlueprintMarker.blueprint_id == row.id)))
    if markers:
        blocks = [{"id": f"marker-{m.id}", "label": m.label, "x": round((m.normalized_x-.5)*24, 2),
                   "z": round((m.normalized_y-.5)*16, 2), "width": 4.2, "depth": 3.6,
                   "height": 2.8 + (m.id % 3)} for m in markers]
    else:
        blocks = [
            {"id":"main-hall","label":"Main hall","x":-2,"z":0,"width":15,"depth":9,"height":5},
            {"id":"utilities","label":"Utilities","x":8,"z":-2,"width":4,"depth":5,"height":3.5},
            {"id":"storage","label":"Storage","x":7,"z":5,"width":6,"depth":4,"height":3},
            {"id":"office","label":"Office","x":-7,"z":6,"width":5,"depth":3,"height":2.5},
        ]
    model = {"model_version":"plan-concept-1.0", "source_blueprint_id":row.id, "conceptual":True,
             "footprint_m":{"width":32,"depth":22}, "roof_area_m2":2450, "blocks":blocks,
             "limitations":"Conceptual extrusion from the uploaded plan; dimensions require user and professional validation."}
    row.extracted_data_json = {**(row.extracted_data_json or {}), "model": model}
    row.processing_status = "model_ready"; db.commit()
    return model


@app.post("/api/blueprints/{blueprint_id}/markers")
def add_marker(blueprint_id: int, body: MarkerIn, db: Session = Depends(get_db), user=Depends(current_user)):
    bp = db.get(Blueprint, blueprint_id)
    if not bp: raise HTTPException(404, "Blueprint not found")
    owned_facility(db, user, bp.facility_id); row = BlueprintMarker(blueprint_id=blueprint_id, **body.model_dump()); db.add(row); db.commit(); db.refresh(row); return as_dict(row)


@app.patch("/api/blueprint-markers/{marker_id}")
def edit_marker(marker_id: int, body: MarkerIn, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(BlueprintMarker, marker_id)
    if not row: raise HTTPException(404, "Marker not found")
    bp = db.get(Blueprint, row.blueprint_id); owned_facility(db, user, bp.facility_id)
    for key, value in body.model_dump().items(): setattr(row, key, value)
    db.commit(); db.refresh(row); return as_dict(row)


@app.delete("/api/blueprint-markers/{marker_id}")
def delete_marker(marker_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(BlueprintMarker, marker_id)
    if not row: raise HTTPException(404, "Marker not found")
    bp = db.get(Blueprint, row.blueprint_id); owned_facility(db, user, bp.facility_id); db.delete(row); db.commit(); return {"deleted": True}


@app.post("/api/sites/screen")
def screen_site(body: FacilityIn, user=Depends(current_user)):
    return {"site": body.model_dump(), "coverage": {"weather_history": "available through provider adapter", "validated_flood_map": "unavailable", "official_warnings": "not connected"},
            "considerations": ["Review drainage with a qualified professional", "Confirm local planning and flood requirements", "Validate critical equipment placement"],
            "limitations": "Preliminary screening only; not a planning, flood-risk, geotechnical, or engineering assessment."}


@app.post("/api/sites/compare")
def compare_sites(payload: Dict[str, Any], user=Depends(current_user)):
    return {"configurations": payload, "conclusion": "Differences reflect user-selected conceptual measures only.", "professional_review_required": True}


@app.post("/api/sites/evaluate")
def evaluate_site(body: SiteEvaluationIn, user=Depends(current_user)):
    preset = next((x for x in SITE_PRESETS if x["id"] == body.preset_id), None)
    if not preset: raise HTTPException(404, "Planning location not found")
    simulations = {k: max(0, min(100, int(v))) for k, v in body.simulations.items()}
    combined = {k: round(preset["hazards"].get(k, 0) * .55 + simulations.get(k, 50) * .45) for k in preset["hazards"]}
    highest = sorted(combined.items(), key=lambda x: x[1], reverse=True)
    max_score = highest[0][1]
    decision = "conditional" if max_score >= 67 else "review" if max_score >= 40 else "favourable"
    harvest_m3 = round(preset["annual_rainfall_mm"] / 1000 * body.roof_area_m2 * .8)
    carbon_low = round(body.roof_area_m2 * 0.42)
    actions = {
        "wind":"Obtain structural wind-load review", "rain":"Size roof drainage against local design rainfall",
        "flood":"Validate finished-floor level and evacuation access", "heat":"Model cooling loads and shaded operations",
        "wildfire":"Review defensible space and smoke filtration", "drought":"Prepare a water-efficiency and reuse plan",
    }
    return {"preset":preset, "facility_type":body.facility_type, "hazard_scores":combined,
            "decision":decision, "highest_hazards":[{"hazard":k,"score":v,"action":actions[k]} for k,v in highest[:3]],
            "carbon":{"embodied_range_tco2e":[carbon_low,round(carbon_low*1.45)],"grid_intensity_gco2_kwh":preset["grid_carbon_gco2_kwh"]},
            "rainwater":{"annual_capture_potential_m3":harvest_m3,"score":preset["rainwater_score"]},
            "limitations":"Synthetic preliminary screening. Not a planning, engineering, carbon-accounting, or hazard certification."}


@app.post("/api/reports")
def create_report(body: ReportIn, db: Session = Depends(get_db), user=Depends(current_user)):
    facility = owned_facility(db, user, body.facility_id)
    if body.scenario_id:
        scenario = db.get(Scenario, body.scenario_id)
        if not scenario or scenario.facility_id != facility.id: raise HTTPException(422, "Invalid scenario")
    row = Report(user_id=user.id, facility_id=facility.id, scenario_id=body.scenario_id, report_type=body.report_type, title=body.title)
    db.add(row); db.flush(); path = UPLOAD_DIR / f"report-{row.id}.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4); pdf.setTitle(body.title); pdf.setFont("Helvetica-Bold", 18); pdf.drawString(54, 790, "BeforeImpact AI")
    pdf.setFont("Helvetica", 12); pdf.drawString(54, 760, body.title); pdf.drawString(54, 735, facility.name); pdf.drawString(54, 700, "Illustrative climate-resilience scenario report")
    pdf.drawString(54, 675, "Not an engineering, safety, insurance, or certified flood-risk assessment."); pdf.save()
    row.file_path = str(path); db.commit(); db.refresh(row); return as_dict(row)


@app.get("/api/reports")
def reports(db: Session = Depends(get_db), user=Depends(current_user)):
    return [as_dict(x) for x in db.scalars(select(Report).where(Report.user_id == user.id).order_by(Report.id.desc()))]


@app.get("/api/reports/{report_id}")
def report(report_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(Report, report_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Report not found")
    return as_dict(row)


@app.get("/api/reports/{report_id}/download")
def report_download(report_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(Report, report_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Report not found")
    return FileResponse(row.file_path, filename=f"beforeimpact-report-{row.id}.pdf", media_type="application/pdf")


@app.get("/api/demo/status")
def demo_status(db: Session = Depends(get_db)):
    return {"ready": bool(db.scalar(select(User).where(User.email == DEMO_EMAIL))), "credentials": {"email": DEMO_EMAIL, "password": "Demo123!"}, "synthetic_data": True}


@app.post("/api/demo/reset")
def demo_reset(db: Session = Depends(get_db), user=Depends(current_user)):
    if os.getenv("APP_ENV", "demo") not in ("demo", "development"): raise HTTPException(403, "Demo reset is disabled")
    if user.email != DEMO_EMAIL: raise HTTPException(403, "Demo account required")
    db.execute(delete(User).where(User.email == DEMO_EMAIL)); db.commit(); seed_demo(); return {"reset": True}
