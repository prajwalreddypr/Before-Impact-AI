import hashlib
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from .db import Base, SessionLocal, engine
from .models import (Asset, Blueprint, BlueprintMarker, Facility, PreparationAction,
                     Scenario, ScenarioResult, User, Warning, WeatherEvent, WeatherReading)
from .scenario import calculate_exposure


DEMO_EMAIL = "demo@beforeimpact.ai"


def password_hash(password):
    return "sha256$" + hashlib.sha256(("beforeimpact-demo:" + password).encode()).hexdigest()


FACILITIES = [
    ("GreenVale Greenhouses", "greenhouse", "Agriculture", "France", "Outside Lyon · fictional", 45.77, 4.83, "Europe/Paris", "EUR", "existing"),
    ("Riverside Distribution Centre", "warehouse", "Logistics", "Germany", "Rhine district · fictional", 50.11, 8.68, "Europe/Berlin", "EUR", "existing"),
    ("Sunfield Farm", "farm", "Agriculture", "India", "Maharashtra · fictional", 19.07, 72.88, "Asia/Kolkata", "INR", "existing"),
    ("Coastal Workshop", "workshop", "Marine services", "Portugal", "Atlantic coast · fictional", 38.72, -9.14, "Europe/Lisbon", "EUR", "existing"),
    ("Urban Manufacturing Plant", "factory", "Manufacturing", "United States", "Midwest district · fictional", 41.88, -87.63, "America/Chicago", "USD", "existing"),
    ("Future Logistics Hub", "warehouse", "Logistics", "Netherlands", "Rotterdam region · proposed", 51.92, 4.48, "Europe/Amsterdam", "EUR", "proposed"),
]

GREEN_ASSETS = [
    ("Greenhouse A", "greenhouse", 185000, -4, 0, -1, {"width": 3.5, "height": 2.3, "depth": 7}, {"wind": "high", "flood": "medium"}),
    ("Greenhouse B", "greenhouse", 195000, 0, 0, -1, {"width": 3.5, "height": 2.3, "depth": 7}, {"wind": "high", "flood": "medium"}),
    ("Greenhouse C", "greenhouse", 180000, 4, 0, -1, {"width": 3.5, "height": 2.3, "depth": 7}, {"wind": "high", "flood": "medium"}),
    ("Storage shed", "building", 95000, 7, 0, 4, {"width": 4, "height": 2.8, "depth": 4}, {"wind": "medium"}),
    ("Water tank", "water", 18000, -8, 0, 4, {"radius": 1.3, "height": 3}, {"wind": "low"}),
    ("Irrigation pump", "equipment", 32000, -6, 0, 5, {"width": 1.5}, {"flood": "high"}),
    ("Crop inventory", "crop", 145000, 0, 0, 0, {"area": 4200}, {"heat": "high", "wind": "medium"}),
    ("Electrical cabinet", "electrical", 28000, 6, 0, 1, {"width": 1}, {"flood": "high"}),
    ("Movable equipment", "machinery", 54000, -7, 0, -5, {"width": 2}, {"wind": "high"}),
    ("Access road", "road", 40000, 0, 0, 8, {"length": 20}, {"flood": "medium"}),
]

ACTION_TITLES = {
    "wind": ["Secure loose outdoor equipment", "Move portable stock indoors", "Inspect approved anchoring", "Latch doors and vents", "Clear safe access routes", "Back up operating records", "Confirm staff contact tree", "Pause exposed lifting work"],
    "rain": ["Inspect roof drainage", "Clear safe surface drains", "Move water-sensitive stock", "Check temporary covers", "Protect document storage", "Review safe access routes", "Confirm pump readiness", "Monitor official updates"],
    "flood": ["Raise portable inventory", "Isolate vulnerable electrics", "Position approved barriers", "Move vehicles to higher ground", "Verify evacuation routes", "Protect critical records", "Confirm pump maintenance", "Request professional flood review"],
    "heat": ["Reschedule exposed work", "Check cooling equipment", "Protect temperature-sensitive stock", "Provide shaded rest areas", "Review hydration plan", "Monitor indoor heat", "Inspect refrigeration alarms", "Plan welfare check-ins"],
    "wildfire": ["Clear safe access routes", "Move combustibles from structures", "Check smoke filtration", "Protect critical records", "Review evacuation triggers", "Confirm staff contacts"],
    "drought": ["Review water reserves", "Inspect irrigation leaks", "Prioritise critical water use", "Protect sensitive stock", "Check soil moisture", "Request water-plan review"],
}


def _event_series(db, facility, name, hazard, offset_days, depth=0, mode="historical"):
    start = datetime(2025, 1, 20, tzinfo=timezone.utc) + timedelta(days=offset_days)
    peak = start + timedelta(hours=24)
    event = WeatherEvent(facility_id=facility.id, name=name, hazard_type=hazard, event_mode=mode,
                         start_at=start, peak_at=peak, end_at=start + timedelta(hours=48),
                         provider="BeforeImpact reproducible demo", source_url="", is_synthetic=True,
                         scenario_depth_m=depth)
    db.add(event); db.flush()
    for hour in range(49):
        curve = math.exp(-((hour - 24) / 9) ** 2)
        vals = {
            "wind": (16 + 38 * curve, 24 + 72 * curve, .4 * curve, 14 - curve),
            "rain": (10 + 15 * curve, 18 + 24 * curve, 1 + 18 * curve, 15 - 2 * curve),
            "flood": (8 + 8 * curve, 15 + 12 * curve, 1 + 9 * curve, 13),
            "heat": (7 + 4 * curve, 11 + 5 * curve, 0, 28 + 14 * curve),
            "wildfire": (12 + 20 * curve, 20 + 32 * curve, 0, 26 + 10 * curve),
            "drought": (8 + 5 * curve, 14 + 8 * curve, 0, 30 + 8 * curve),
            "normal": (8, 13, 0, 19),
        }[hazard]
        db.add(WeatherReading(weather_event_id=event.id, timestamp=start + timedelta(hours=hour),
                              wind_speed_kmh=round(vals[0], 1), wind_gust_kmh=round(vals[1], 1),
                              wind_direction_deg=(220 + hour * 3) % 360, rainfall_mm=round(vals[2], 1),
                              temperature_c=round(vals[3], 1), apparent_temperature_c=round(vals[3] + (3 if hazard == "heat" else 0), 1),
                              relative_humidity=85 if hazard in ("rain", "flood") else 48,
                              source_type="synthetic_demo", quality_metadata_json={"synthetic": True, "seed": 2026}))
    return event


def _ensure_climate_portfolio(db, user):
    facilities = {f.name: f for f in db.scalars(select(Facility).where(Facility.owner_user_id == user.id))}
    additions = [
        ("Coastal Workshop", "Coastal fire-weather window", "wildfire", 275),
        ("Urban Manufacturing Plant", "Extended dry-period stress", "drought", 305),
    ]
    for facility_name, event_name, hazard, offset in additions:
        facility = facilities.get(facility_name)
        if facility and not db.scalar(select(WeatherEvent).where(WeatherEvent.name == event_name)):
            _event_series(db, facility, event_name, hazard, offset, mode="what_if")
    db.flush()

    for hazard, titles in ACTION_TITLES.items():
        if db.scalar(select(PreparationAction).where(PreparationAction.hazard_type == hazard)):
            continue
        for i, title in enumerate(titles):
            db.add(PreparationAction(hazard_type=hazard, asset_type="all", title=title,
                description="Complete only while conditions are safe.",
                rationale=f"Reduces avoidable {hazard} exposure under the stated assumptions.",
                estimated_minutes=15 + (i % 3) * 15, priority="high" if i < 2 else "medium",
                safety_conditions_json={"follow_official_guidance": True},
                references_json=[{"title": "Ready.gov hazard guidance", "url": "https://www.ready.gov/"}],
                professional_review=("review" in title.lower())))
    db.flush()

    warning_specs = [
        ("GreenVale Greenhouses", "wind", "severe", "Severe wind"),
        ("Riverside Distribution Centre", "flood", "severe", "Flood scenario"),
        ("Riverside Distribution Centre", "rain", "moderate", "Heavy rain"),
        ("Sunfield Farm", "heat", "severe", "Extreme heat"),
        ("Coastal Workshop", "wildfire", "high", "Fire weather"),
        ("Urban Manufacturing Plant", "drought", "moderate", "Drought stress"),
    ]
    for facility_name, hazard, severity, title in warning_specs:
        facility = facilities.get(facility_name)
        if not facility or db.scalar(select(Warning).where(Warning.facility_id == facility.id, Warning.hazard_type == hazard)):
            continue
        event = db.scalar(select(WeatherEvent).where(WeatherEvent.facility_id == facility.id, WeatherEvent.hazard_type == hazard).order_by(WeatherEvent.id))
        if event:
            db.add(Warning(facility_id=facility.id, weather_event_id=event.id, hazard_type=hazard,
                severity=severity, title=title, issued_at=event.start_at - timedelta(hours=6),
                valid_from=event.start_at, valid_to=event.end_at, provider="BeforeImpact synthetic demo",
                text=f"{title} signal for {facility.name}.", is_synthetic=True))


def seed_demo():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        existing_user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if existing_user:
            _ensure_climate_portfolio(db, existing_user)
            db.commit()
            return
        user = User(email=DEMO_EMAIL, password_hash=password_hash("Demo123!"), display_name="Alex Morgan")
        db.add(user); db.flush()
        facilities = []
        for values in FACILITIES:
            f = Facility(owner_user_id=user.id, name=values[0], facility_type=values[1], industry=values[2], country=values[3],
                         address_label=values[4], latitude=values[5], longitude=values[6], timezone=values[7], currency=values[8], status=values[9])
            db.add(f); db.flush(); facilities.append(f)
        for name, kind, value, x, y, z, dims, vuln in GREEN_ASSETS:
            db.add(Asset(facility_id=facilities[0].id, name=name, asset_type=kind, description="Synthetic demonstration asset",
                         value_amount=value, currency="EUR", relative_x=x, relative_y=y, relative_z=z,
                         dimensions_json=dims, vulnerability_profile_json=vuln))
        other_assets = {
            1: [("Main warehouse", "warehouse", 1200000), ("Refrigerated inventory", "inventory", 480000), ("Loading bay electrics", "electrical", 90000)],
            2: [("Cold room", "building", 220000), ("Stored harvest", "inventory", 160000), ("Irrigation equipment", "equipment", 85000)],
            3: [("Workshop building", "building", 460000), ("Outdoor tools", "machinery", 75000)],
            4: [("Assembly hall", "building", 2100000), ("Control systems", "electrical", 340000)],
            5: [("Concept warehouse", "warehouse", 1600000), ("Planned inventory", "inventory", 600000)],
        }
        for index, rows in other_assets.items():
            for n, kind, value in rows:
                db.add(Asset(facility_id=facilities[index].id, name=n, asset_type=kind, description="Synthetic demonstration asset",
                             value_amount=value, currency=facilities[index].currency, relative_x=index * 2, relative_y=0, relative_z=index))
        db.flush()
        events = [
            _event_series(db, facilities[0], "Storm Céleste", "wind", 0),
            _event_series(db, facilities[0], "Autumn wind event", "wind", 62),
            _event_series(db, facilities[1], "Riverside inundation 0.8 m", "flood", 91, .8, "what_if"),
            _event_series(db, facilities[1], "Riverside inundation 1.4 m", "flood", 122, 1.4, "what_if"),
            _event_series(db, facilities[1], "Persistent rainfall", "rain", 145),
            _event_series(db, facilities[2], "Monsoon rainfall", "rain", 180),
            _event_series(db, facilities[2], "Summer heatwave", "heat", 210),
            _event_series(db, facilities[0], "Normal weather baseline", "normal", 250),
        ]
        for hazard, titles in ACTION_TITLES.items():
            for i, title in enumerate(titles):
                db.add(PreparationAction(hazard_type=hazard, asset_type="all", title=title,
                    description="Review and complete only while conditions are safe.",
                    rationale=f"Reduces avoidable {hazard} exposure under the stated scenario assumptions.",
                    estimated_minutes=15 + (i % 4) * 15, priority="high" if i < 3 else "medium",
                    safety_conditions_json={"stop_when_conditions_worsen": True, "follow_official_guidance": True},
                    references_json=[{"title": "Ready.gov severe weather guidance", "url": "https://www.ready.gov/"}],
                    professional_review=("professional" in title.lower() or "anchoring" in title.lower())))
        db.flush()
        assets = list(db.scalars(select(Asset).where(Asset.facility_id == facilities[0].id)))
        for name, selected in [("Scenario A · No preparation", []), ("Scenario B · Selected preparations", [1, 2, 4])]:
            s = Scenario(facility_id=facilities[0].id, weather_event_id=events[0].id, name=name,
                         scenario_type="prepared" if selected else "unprepared", assumptions_json={"selected_action_ids": selected})
            db.add(s); db.flush(); db.add(ScenarioResult(scenario_id=s.id, results_json=calculate_exposure(assets, events[0], selected)))
        upload_dir = Path(__file__).resolve().parents[1] / "uploads"
        upload_dir.mkdir(exist_ok=True)
        blueprint_path = upload_dir / "synthetic-logistics-blueprint.svg"
        blueprint_path.write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="650" viewBox="0 0 1000 650"><rect width="1000" height="650" fill="#f7f8f5"/><g fill="none" stroke="#243b37" stroke-width="6"><rect x="70" y="60" width="860" height="520"/><path d="M70 420h860M340 60v360M720 60v360"/><rect x="110" y="110" width="180" height="240"/><rect x="390" y="110" width="280" height="240"/><rect x="770" y="110" width="110" height="240"/></g><g font-family="Arial" font-size="25" fill="#243b37"><text x="130" y="150">STORAGE</text><text x="440" y="150">SORTING HALL</text><text x="780" y="150">ELECTRICAL</text><text x="400" y="490">LOADING / ACCESS</text><text x="70" y="625">SYNTHETIC CONCEPT PLAN · NOT FOR CONSTRUCTION</text></g></svg>''', encoding="utf-8")
        bp = Blueprint(facility_id=facilities[5].id, filename=blueprint_path.name, storage_path=str(blueprint_path), mime_type="image/svg+xml", processing_status="ready", extracted_data_json={"synthetic": True})
        db.add(bp); db.flush()
        for label, x, y in [("Storage", .2, .35), ("Sorting hall", .5, .35), ("Electrical", .82, .35)]:
            db.add(BlueprintMarker(blueprint_id=bp.id, normalized_x=x, normalized_y=y, label=label, marker_type="asset"))
        _ensure_climate_portfolio(db, user)
        db.commit()


if __name__ == "__main__":
    seed_demo()
    print("BeforeImpact demo data ready")
