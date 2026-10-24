from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ConstructionProject(Base):
    __tablename__ = "construction_projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    building_type: Mapped[str] = mapped_column(String(80), default="School")
    region: Mapped[str] = mapped_column(String(120), default="Japan")
    entry_mode: Mapped[str] = mapped_column(String(30), default="find")
    active_section: Mapped[str] = mapped_column(String(40), default="projects")
    selected_site_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    project_data_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Facility(Base):
    __tablename__ = "facilities"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    facility_type: Mapped[str] = mapped_column(String(80))
    industry: Mapped[str] = mapped_column(String(80))
    country: Mapped[str] = mapped_column(String(80))
    address_label: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    timezone: Mapped[str] = mapped_column(String(80), default="UTC")
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    status: Mapped[str] = mapped_column(String(20), default="existing")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    asset_type: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    value_amount: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    relative_x: Mapped[float] = mapped_column(Float, default=0)
    relative_y: Mapped[float] = mapped_column(Float, default=0)
    relative_z: Mapped[float] = mapped_column(Float, default=0)
    dimensions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    vulnerability_profile_json: Mapped[dict] = mapped_column(JSON, default=dict)
    preparedness_status: Mapped[str] = mapped_column(String(30), default="unreviewed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WeatherEvent(Base):
    __tablename__ = "weather_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    hazard_type: Mapped[str] = mapped_column(String(30), index=True)
    event_mode: Mapped[str] = mapped_column(String(30))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    peak_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str] = mapped_column(String(100))
    source_url: Mapped[str] = mapped_column(String(500), default="")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    scenario_depth_m: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WeatherReading(Base):
    __tablename__ = "weather_readings"
    __table_args__ = (Index("ix_reading_event_timestamp", "weather_event_id", "timestamp"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    weather_event_id: Mapped[int] = mapped_column(ForeignKey("weather_events.id", ondelete="CASCADE"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    wind_speed_kmh: Mapped[float] = mapped_column(Float, default=0)
    wind_gust_kmh: Mapped[float] = mapped_column(Float, default=0)
    wind_direction_deg: Mapped[float] = mapped_column(Float, default=0)
    rainfall_mm: Mapped[float] = mapped_column(Float, default=0)
    temperature_c: Mapped[float] = mapped_column(Float, default=20)
    apparent_temperature_c: Mapped[float] = mapped_column(Float, default=20)
    relative_humidity: Mapped[float] = mapped_column(Float, default=60)
    source_type: Mapped[str] = mapped_column(String(60), default="synthetic_demo")
    quality_metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Warning(Base):
    __tablename__ = "warnings"
    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), index=True)
    weather_event_id: Mapped[int] = mapped_column(ForeignKey("weather_events.id", ondelete="CASCADE"), index=True)
    hazard_type: Mapped[str] = mapped_column(String(30), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(180))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str] = mapped_column(String(120), default="BeforeImpact demo")
    text: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)


class PreparationAction(Base):
    __tablename__ = "preparation_actions"
    id: Mapped[int] = mapped_column(primary_key=True)
    hazard_type: Mapped[str] = mapped_column(String(30), index=True)
    asset_type: Mapped[str] = mapped_column(String(80), default="all")
    title: Mapped[str] = mapped_column(String(220))
    description: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=30)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    safety_conditions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    references_json: Mapped[list] = mapped_column(JSON, default=list)
    professional_review: Mapped[bool] = mapped_column(Boolean, default=False)


class PreparationPlan(Base):
    __tablename__ = "preparation_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), index=True)
    weather_event_id: Mapped[int] = mapped_column(ForeignKey("weather_events.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(30), default="active")
    generated_by: Mapped[str] = mapped_column(String(30), default="deterministic_fallback")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PlanItem(Base):
    __tablename__ = "plan_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("preparation_plans.id", ondelete="CASCADE"), index=True)
    action_id: Mapped[int] = mapped_column(ForeignKey("preparation_actions.id"))
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="suggested")
    completion_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    user_notes: Mapped[str] = mapped_column(Text, default="")
    assignee_name: Mapped[str] = mapped_column(String(120), default="Unassigned")


class Scenario(Base):
    __tablename__ = "scenarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), index=True)
    weather_event_id: Mapped[int] = mapped_column(ForeignKey("weather_events.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(180))
    scenario_type: Mapped[str] = mapped_column(String(40), default="prepared")
    assumptions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    model_version: Mapped[str] = mapped_column(String(30), default="exposure-1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ScenarioResult(Base):
    __tablename__ = "scenario_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), unique=True)
    results_json: Mapped[dict] = mapped_column(JSON)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Blueprint(Base):
    __tablename__ = "blueprints"
    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(80))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    processing_status: Mapped[str] = mapped_column(String(30), default="ready")
    extracted_data_json: Mapped[dict] = mapped_column(JSON, default=dict)


class BlueprintMarker(Base):
    __tablename__ = "blueprint_markers"
    id: Mapped[int] = mapped_column(primary_key=True)
    blueprint_id: Mapped[int] = mapped_column(ForeignKey("blueprints.id", ondelete="CASCADE"), index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=True)
    normalized_x: Mapped[float] = mapped_column(Float)
    normalized_y: Mapped[float] = mapped_column(Float)
    label: Mapped[str] = mapped_column(String(180))
    marker_type: Mapped[str] = mapped_column(String(80), default="asset")


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"))
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), nullable=True)
    report_type: Mapped[str] = mapped_column(String(50), default="scenario_summary")
    title: Mapped[str] = mapped_column(String(200))
    file_path: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
