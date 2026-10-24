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
from .models import (Asset, Blueprint, BlueprintMarker, ConstructionProject, Facility, PlanItem,
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

def demo_site(site_id, name, region, lat, lon, plot, rainfall, carbon, hazards, zone, coverage, far, height, sensitivity, completeness, country="Japan"):
    return {"id":site_id,"name":name,"region":region,"country":country,"latitude":lat,"longitude":lon,
            "plot_area_m2":plot,"site_geometry":[[0,0],[1,0],[1,.7],[.15,1]],"land_use":zone,
            "planning":{"compatibility":"Preliminarily compatible","coverage_ratio_pct":coverage,"floor_area_ratio_pct":far,
                        "height_note":height,"setback_m":3,"road_access":"6 m conceptual access road",
                        "seismic":"Engineer-designed seismic system required","flood_note":"Municipal verification required"},
            "annual_rainfall_mm":rainfall,"grid_carbon_gco2_kwh":carbon,"rainwater_score":round(min(95,rainfall/20)),
            "hazards":hazards,"environment":{"sensitivity":sensitivity,"protected_overlap":"None in demo record","developed_land_pct":68},
            "air_quality":{"pm25":11.2,"pm10":22.4,"no2":18.0,"o3":41.0,"so2":2.1,"co":0.4,"period":"Synthetic annual profile 2025"},
            "regional_ghg":{"co2_kt":1240,"ch4_ktco2e":84,"n2o_ktco2e":31,"year":2024},
            "data_completeness":completeness,"status":"synthetic","source":"BeforeImpact curated hackathon dataset","retrieved":"2026-10-24"}


SITE_PRESETS = [
    demo_site("osaka-river","Osaka Riverside A","Kansai",34.67,135.46,6800,1340,412,{"rain":68,"flood":76,"wind":60,"heat":72,"wildfire":18,"earthquake":64},"Quasi-industrial demo zone",60,200,"Envelope depends on district controls","Previously developed river corridor",91),
    demo_site("nagoya-hills","Nagoya Hills B","Chubu",35.16,137.02,9200,1580,420,{"rain":72,"flood":34,"wind":62,"heat":66,"wildfire":44,"earthquake":61},"Educational/community demo zone",50,150,"No fixed demo floor cap; envelope review needed","Vegetated edge; retain mature trees",86),
    demo_site("fukuoka-transit","Fukuoka Transit C","Kyushu",33.58,130.42,7400,1685,451,{"rain":84,"flood":55,"wind":78,"heat":73,"wildfire":28,"earthquake":48},"Mixed-use demo zone",70,300,"Aviation and street-plane checks unknown","Developed urban infill",89),
    demo_site("sendai-upland","Sendai Upland D","Tohoku",38.29,140.91,12000,1250,401,{"rain":57,"flood":22,"wind":69,"heat":42,"wildfire":35,"earthquake":79},"Community facility demo zone",50,100,"Landscape-height review assumed","Low ecological sensitivity in demo",82),
    demo_site("tokyo-bay","Tokyo Bay Edge E","Kanto",35.59,139.80,5600,1600,438,{"rain":77,"flood":88,"wind":70,"heat":79,"wildfire":12,"earthquake":72},"Commercial demo zone",80,400,"Complex district envelope; municipal review essential","Reclaimed/developed conceptual plot",94),
    demo_site("sapporo-north","Sapporo North F","Hokkaido",43.11,141.35,10800,1145,465,{"rain":39,"flood":31,"wind":58,"heat":23,"wildfire":33,"earthquake":51},"Institutional demo zone",50,120,"Snow-loading envelope not represented","Developed land near open landscape",80),
    demo_site("kobe-harbor","Kobe Harbor G","Kansai",34.68,135.19,6300,1275,409,{"rain":65,"flood":82,"wind":67,"heat":69,"wildfire":22,"earthquake":83},"Harbor-service demo zone",60,200,"Port and coastal controls unknown","Industrial brownfield concept",84),
    demo_site("kyoto-west","Kyoto West H","Kansai",35.01,135.68,8300,1490,416,{"rain":66,"flood":41,"wind":45,"heat":76,"wildfire":55,"earthquake":58},"Community demo zone",40,100,"Landscape and heritage review may apply","Vegetation corridor nearby",78),
    demo_site("lyon-east","Lyon East Plot","Auvergne-Rhône-Alpes",45.75,4.94,7800,832,56,{"rain":46,"flood":38,"wind":34,"heat":67,"wildfire":29,"earthquake":20},"Mixed community demo zone",60,180,"Local envelope review required","Previously developed urban edge",91,"France"),
    demo_site("nantes-loire","Nantes Loire Plot","Pays de la Loire",47.22,-1.47,9600,820,52,{"rain":55,"flood":66,"wind":58,"heat":38,"wildfire":18,"earthquake":12},"Institutional demo zone",50,150,"River-corridor review required","Developed riverside context",88,"France"),
    demo_site("lille-south","Lille South Plot","Hauts-de-France",50.58,3.05,6400,742,49,{"rain":43,"flood":42,"wind":61,"heat":34,"wildfire":12,"earthquake":10},"Urban community demo zone",65,220,"Municipal massing review required","Brownfield regeneration concept",93,"France"),
    demo_site("bordeaux-west","Bordeaux West Plot","Nouvelle-Aquitaine",44.84,-0.66,11200,944,54,{"rain":58,"flood":51,"wind":55,"heat":63,"wildfire":69,"earthquake":13},"Mixed-use demo zone",50,160,"Landscape and wildfire review required","Urban edge near vegetation",84,"France"),
    demo_site("marseille-north","Marseille North Plot","Provence-Alpes-Côte d’Azur",43.36,5.37,8700,515,47,{"rain":42,"flood":48,"wind":76,"heat":82,"wildfire":84,"earthquake":18},"Community facility demo zone",45,140,"Fire-access and height review required","Dry vegetated urban fringe",86,"France"),
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


class ConstructionProjectIn(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    building_type: str = "School"
    region: str = "Japan"
    entry_mode: str = "find"
    active_section: str = "projects"
    selected_site_ids: List[str] = []
    data: Dict[str, Any] = {}


class ConstructionProjectPatch(BaseModel):
    name: Optional[str] = None
    building_type: Optional[str] = None
    region: Optional[str] = None
    entry_mode: Optional[str] = None
    active_section: Optional[str] = None
    selected_site_ids: Optional[List[str]] = None
    data: Optional[Dict[str, Any]] = None


class SiteSearchIn(BaseModel):
    building_type: str = "School"
    region: str = "Japan"
    minimum_land_area_m2: float = Field(default=4000, ge=0)
    building_area_m2: float = Field(default=1800, ge=50)
    floors: int = Field(default=2, ge=1, le=80)
    priority: str = "balanced"


class GeometryIn(BaseModel):
    building_type: str = "School"
    width_m: float = Field(default=42, ge=4, le=500)
    depth_m: float = Field(default=28, ge=4, le=500)
    floors: int = Field(default=2, ge=1, le=80)
    floor_height_m: float = Field(default=3.6, ge=2, le=12)
    zones: List[str] = []


class SimulationRunIn(BaseModel):
    site_id: str
    hazard: str
    intensity: float = Field(ge=0)
    finished_floor_m: float = Field(default=.2, ge=0, le=20)
    equipment_level_m: float = Field(default=.3, ge=0, le=100)
    orientation_deg: float = Field(default=0, ge=0, le=360)
    baseline_floor_m: float = Field(default=.2, ge=0, le=20)


class SustainabilityIn(BaseModel):
    site_id: str
    roof_area_m2: float = Field(ge=1)
    collection_efficiency: float = Field(default=.8, ge=.1, le=1)
    storage_m3: float = Field(default=250, ge=0)
    concrete_t: float = Field(default=1200, ge=0)
    steel_t: float = Field(default=180, ge=0)
    timber_t: float = Field(default=40, ge=0)
    insulation_t: float = Field(default=25, ge=0)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "BeforeImpact AI", "model_version": "exposure-1.0"}


@app.get("/api/site-presets")
def site_presets(user=Depends(current_user)):
    return {"locations": SITE_PRESETS, "synthetic": True,
            "notice": "Synthetic planning dataset for product demonstration; validate with authoritative local sources."}


def project_payload(row):
    data = as_dict(row)
    data["selected_site_ids"] = data.pop("selected_site_ids_json") or []
    data["data"] = data.pop("project_data_json") or {}
    return data


@app.get("/api/construction-projects")
def construction_projects(db: Session = Depends(get_db), user=Depends(current_user)):
    rows = db.scalars(select(ConstructionProject).where(ConstructionProject.owner_user_id == user.id).order_by(ConstructionProject.updated_at.desc()))
    return [project_payload(x) for x in rows]


@app.post("/api/construction-projects")
def create_construction_project(body: ConstructionProjectIn, db: Session = Depends(get_db), user=Depends(current_user)):
    row = ConstructionProject(owner_user_id=user.id, name=body.name, building_type=body.building_type,
        region=body.region, entry_mode=body.entry_mode, active_section=body.active_section,
        selected_site_ids_json=body.selected_site_ids, project_data_json=body.data)
    db.add(row); db.commit(); db.refresh(row)
    return project_payload(row)


@app.get("/api/construction-projects/{project_id}")
def get_construction_project(project_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(ConstructionProject, project_id)
    if not row or row.owner_user_id != user.id: raise HTTPException(404, "Project not found")
    return project_payload(row)


@app.patch("/api/construction-projects/{project_id}")
def update_construction_project(project_id: int, body: ConstructionProjectPatch, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(ConstructionProject, project_id)
    if not row or row.owner_user_id != user.id: raise HTTPException(404, "Project not found")
    values = body.model_dump(exclude_unset=True)
    if "selected_site_ids" in values: row.selected_site_ids_json = values.pop("selected_site_ids")
    if "data" in values: row.project_data_json = values.pop("data")
    for key, value in values.items(): setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc); db.commit(); db.refresh(row)
    return project_payload(row)


@app.post("/api/candidate-sites/search")
def search_candidate_sites(body: SiteSearchIn, user=Depends(current_user)):
    matches = []
    weights = {"hazard":.5,"environment":.2,"sustainability":.15,"planning":.15}
    if body.priority == "lower_environmental_impact": weights = {"hazard":.25,"environment":.5,"sustainability":.15,"planning":.1}
    if body.priority == "sustainability": weights = {"hazard":.25,"environment":.15,"sustainability":.5,"planning":.1}
    requested_region = body.region.strip().lower()
    candidates = [x for x in SITE_PRESETS if requested_region in {x["country"].lower(), x["region"].lower()}]
    if not candidates: candidates = SITE_PRESETS
    for site in candidates:
        capacity = site["plot_area_m2"] * site["planning"]["coverage_ratio_pct"] / 100
        eligible = site["plot_area_m2"] >= body.minimum_land_area_m2 and capacity >= body.building_area_m2
        hazard = round(100 - sum(site["hazards"].values()) / len(site["hazards"]))
        environment = 72 if "developed" in site["environment"]["sensitivity"].lower() else 58
        sustainability = round((site["rainwater_score"] + (100-site["grid_carbon_gco2_kwh"]/6))/2)
        planning = 85 if eligible else 30
        score = round(hazard*weights["hazard"]+environment*weights["environment"]+sustainability*weights["sustainability"]+planning*weights["planning"])
        matches.append({**site,"eligible":eligible,"comparison_components":{"lower_hazard":hazard,"environmental_context":environment,"sustainability":sustainability,"planning_fit":planning},
                        "comparison_score":score,"included_because":f"{site['plot_area_m2']:,} m² plot; conceptual coverage capacity {capacity:,.0f} m²."})
    matches.sort(key=lambda x:(x["eligible"],x["comparison_score"]),reverse=True)
    return {"sites":matches,"weights":weights,"notice":"Transparent comparison of fictional demo plots; not a land-availability or permission claim."}


@app.post("/api/simulations/run")
def run_construction_simulation(body: SimulationRunIn, user=Depends(current_user)):
    site = next((x for x in SITE_PRESETS if x["id"] == body.site_id), None)
    if not site: raise HTTPException(404, "Candidate site not found")
    units = {"rain":"mm/h","flood":"m","wind":"km/h","heat":"°C","wildfire":"m from fire front","earthquake":"illustrative intensity"}
    thresholds = {"rain":(35,75),"flood":(.3,1),"wind":(70,120),"heat":(34,42),"wildfire":(500,150),"earthquake":(3,6)}
    low, high = thresholds.get(body.hazard,(33,67))
    if body.hazard == "wildfire": level = "high" if body.intensity <= high else "moderate" if body.intensity <= low else "low"
    else: level = "low" if body.intensity < low else "moderate" if body.intensity < high else "high"
    intersection = body.hazard == "flood" and body.intensity > body.finished_floor_m
    baseline_intersection = body.hazard == "flood" and body.intensity > body.baseline_floor_m
    return {"hazard":body.hazard,"value":body.intensity,"unit":units.get(body.hazard,"scenario units"),"exposure":level,
            "floor_intersection":intersection,"before":{"finished_floor_m":body.baseline_floor_m,"intersects":baseline_intersection},
            "after":{"finished_floor_m":body.finished_floor_m,"intersects":intersection},
            "site_context":site["hazards"].get(body.hazard),"assumption":"User-selected conceptual stress test",
            "limitations":"Geometric exposure illustration only; not structural, hydrological, thermal, fire-spread, or seismic-response analysis."}


@app.post("/api/sustainability/calculate")
def calculate_sustainability(body: SustainabilityIn, user=Depends(current_user)):
    site = next((x for x in SITE_PRESETS if x["id"] == body.site_id), None)
    if not site: raise HTTPException(404, "Candidate site not found")
    annual = body.roof_area_m2 * site["annual_rainfall_mm"] / 1000 * body.collection_efficiency
    factors = {"concrete":.13,"steel":1.85,"timber":.11,"insulation":2.4}
    carbon = body.concrete_t*factors["concrete"]+body.steel_t*factors["steel"]+body.timber_t*factors["timber"]+body.insulation_t*factors["insulation"]
    return {"rainwater":{"annual_potential_m3":round(annual),"storage_m3":body.storage_m3,"formula":"roof area × annual rainfall × collection efficiency","overflow_potential_m3":round(max(0,annual-body.storage_m3))},
            "embodied_carbon":{"estimate_tco2e":round(carbon,1),"factors_tco2e_per_t":factors,"boundary":"Indicative product-stage comparison only"},
            "air_quality":site["air_quality"],"regional_ghg":site["regional_ghg"],"source":site["source"],"status":"synthetic"}


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
def use_demo_blueprint(facility_id: int, plan_type: str = "factory", db: Session = Depends(get_db), user=Depends(current_user)):
    owned_facility(db, user, facility_id)
    source = db.scalar(select(Blueprint).where(Blueprint.mime_type == "image/svg+xml").order_by(Blueprint.id))
    if not source or not Path(source.storage_path).exists():
        raise HTTPException(404, "Demo plan is unavailable")
    plan_type = plan_type.lower() if plan_type.lower() in {"factory","warehouse","residential","school"} else "factory"
    row = Blueprint(facility_id=facility_id, filename=f"demo-{plan_type}-plan.svg", storage_path=source.storage_path,
                    mime_type="image/svg+xml", processing_status="ready", extracted_data_json={"synthetic": True,"plan_type":plan_type})
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
    extracted = row.extracted_data_json or {}
    confirmed = extracted.get("confirmed_geometry")
    plan_type = extracted.get("plan_type", "factory")
    markers = list(db.scalars(select(BlueprintMarker).where(BlueprintMarker.blueprint_id == row.id)))
    if confirmed:
        width, depth = confirmed["width_m"], confirmed["depth_m"]
        floors, floor_height = confirmed["floors"], confirmed["floor_height_m"]
        blocks = [{"id":"confirmed-main","label":confirmed["building_type"],"x":0,"z":0,"width":width,"depth":depth,"height":floors*floor_height}]
        for i, zone in enumerate(confirmed.get("zones",[])[:6]):
            blocks.append({"id":f"zone-{i}","label":zone,"x":-width*.32+(i%3)*width*.32,"z":depth*.28 if i>2 else -depth*.22,"width":width*.22,"depth":depth*.26,"height":floor_height*(1+(i%2)*.35)})
    elif markers:
        blocks = [{"id": f"marker-{m.id}", "label": m.label, "x": round((m.normalized_x-.5)*24, 2),
                   "z": round((m.normalized_y-.5)*16, 2), "width": 4.2, "depth": 3.6,
                   "height": 2.8 + (m.id % 3)} for m in markers]
        width, depth = 32, 22
    else:
        layouts = {
            "school":[{"id":"classrooms","label":"Classroom wing","x":-8,"z":0,"width":18,"depth":7,"height":7.2},{"id":"hall","label":"Community hall","x":8,"z":3,"width":12,"depth":11,"height":6},{"id":"admin","label":"Administration","x":2,"z":-7,"width":9,"depth":5,"height":3.6}],
            "warehouse":[{"id":"storage","label":"Storage hall","x":0,"z":0,"width":28,"depth":17,"height":8},{"id":"loading","label":"Loading bays","x":0,"z":11,"width":22,"depth":4,"height":4}],
            "residential":[{"id":"home","label":"Residential block","x":0,"z":0,"width":16,"depth":12,"height":10.5},{"id":"service","label":"Service core","x":6,"z":-3,"width":4,"depth":5,"height":11}],
            "factory":[{"id":"production","label":"Production hall","x":-3,"z":0,"width":22,"depth":14,"height":7},{"id":"utilities","label":"Utilities","x":11,"z":-3,"width":6,"depth":6,"height":5},{"id":"office","label":"Office","x":8,"z":6,"width":9,"depth":5,"height":3.5}],
        }
        blocks = layouts.get(plan_type, layouts["factory"]); width, depth = (36,26) if plan_type=="school" else (32,22)
    if not confirmed and markers: width, depth = 32, 22
    model = {"model_version":"plan-concept-2.0", "source_blueprint_id":row.id, "conceptual":True,
             "footprint_m":{"width":width,"depth":depth}, "roof_area_m2":round(width*depth), "blocks":blocks,
             "limitations":"Conceptual extrusion from the uploaded plan; dimensions require user and professional validation."}
    row.extracted_data_json = {**(row.extracted_data_json or {}), "model": model}
    row.processing_status = "model_ready"; db.commit()
    return model


@app.put("/api/blueprints/{blueprint_id}/geometry")
def confirm_blueprint_geometry(blueprint_id: int, body: GeometryIn, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(Blueprint, blueprint_id)
    if not row: raise HTTPException(404, "Blueprint not found")
    owned_facility(db, user, row.facility_id)
    row.extracted_data_json = {**(row.extracted_data_json or {}),"confirmed_geometry":body.model_dump(),"geometry_status":"user_confirmed"}
    row.processing_status = "geometry_confirmed"; db.commit(); db.refresh(row)
    return {"blueprint_id":row.id,"status":"confirmed","geometry":body.model_dump(),"notice":"User-confirmed conceptual geometry; professional dimensional verification remains required."}


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
        "wildfire":"Review defensible space and smoke filtration", "earthquake":"Commission code-specific seismic engineering review",
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


@app.post("/api/construction-projects/{project_id}/report")
def create_project_report(project_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    project = db.get(ConstructionProject, project_id)
    if not project or project.owner_user_id != user.id: raise HTTPException(404, "Project not found")
    facility_id = (project.project_data_json or {}).get("facility_id")
    facility = db.get(Facility, facility_id) if facility_id else db.scalar(select(Facility).where(Facility.owner_user_id == user.id))
    if not facility: raise HTTPException(422, "Project needs a linked planning site")
    row = Report(user_id=user.id, facility_id=facility.id, report_type="construction_planning", title=f"{project.name} planning report")
    db.add(row); db.flush(); path = UPLOAD_DIR / f"project-report-{row.id}.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4); width, height = A4; y = height-52
    def line(text, bold=False, gap=17):
        nonlocal y
        if y < 65: pdf.showPage(); y = height-52
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 11 if bold else 9)
        for segment in [str(text)[i:i+96] for i in range(0,len(str(text)),96)] or [""]:
            pdf.drawString(48,y,segment); y -= gap
    pdf.setTitle(row.title); pdf.setFont("Helvetica-Bold",19); pdf.drawString(48,y,"BeforeImpact AI - Construction Planning Report"); y-=28
    line(project.name, True); line(f"Building: {project.building_type} | Region: {project.region} | Demo data status: synthetic")
    data = project.project_data_json or {}; site_ids = project.selected_site_ids_json or []
    sections = [("Project requirements",data.get("requirements",{})),("Selected candidate sites",site_ids),
                ("Confirmed conceptual geometry",data.get("geometry",{})),("Simulations performed",data.get("simulations",{})),
                ("Adaptations tested",data.get("adaptations",{})),("Sustainability assessment",data.get("sustainability",{}))]
    for title, content in sections: line(title,True,18); line(content)
    line("Decision context",True,18); line("Use this report to compare visible assumptions and trade-offs. It does not grant permission or replace architects, engineers, environmental consultants, authorities, or official hazard assessments.")
    line("Data provenance",True,18); line("BeforeImpact curated hackathon dataset; synthetic/modelled status; retrieved 2026-10-24. User-selected stress tests are hypothetical.")
    pdf.save(); row.file_path=str(path); db.commit(); db.refresh(row)
    return as_dict(row)


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
