"""Exhaustive, reproducible comparison of conceptual flood adaptations.

All prices and carbon factors are editable demonstration assumptions, not quotes
or engineering data. Water levels and elevations use the same local datum.
"""
import hashlib
import json
import math
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Assumptions(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    standard_cost_m3: float = Field(default=180, gt=0, le=10000)
    lower_carbon_cost_m3: float = Field(default=215, gt=0, le=10000)
    standard_carbon_kg_m3: float = Field(default=240, ge=0, le=10000)
    lower_carbon_kg_m3: float = Field(default=130, ge=0, le=10000)
    equipment_fixed_cost: float = Field(default=1500, ge=0, le=100000)
    equipment_cost_m: float = Field(default=2400, ge=0, le=100000)
    equipment_fixed_carbon_kg: float = Field(default=80, ge=0, le=10000)
    equipment_carbon_kg_m: float = Field(default=60, ge=0, le=10000)


class ResilienceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    blueprint_id: int = Field(gt=0)
    budget_eur: float = Field(default=300000, ge=0, le=10000000)
    water_level_m: float = Field(default=.8, ge=0, le=5)
    freeboard_m: float = Field(default=.3, ge=0, le=1)
    baseline_floor_m: float = Field(default=.2, ge=0, le=5)
    baseline_equipment_m: float = Field(default=.3, ge=0, le=8)
    max_raise_m: float = Field(default=1.5, ge=0, le=3)
    allow_equipment_raise: bool = True
    protect_floor: bool = True
    assumptions: Assumptions = Field(default_factory=Assumptions)

    @model_validator(mode="after")
    def check_datum(self):
        if self.baseline_equipment_m < self.baseline_floor_m:
            raise ValueError("Equipment elevation must be at or above the baseline floor.")
        return self


class ApplyOption(BaseModel):
    option_id: str = Field(min_length=1, max_length=80)
    study_id: str = Field(min_length=1, max_length=64)


def geometry_fingerprint(geometry):
    return hashlib.sha256(json.dumps(geometry, sort_keys=True).encode()).hexdigest()


def solve(body: ResilienceInput, geometry: dict):
    """Enumerate a 0.1 m catalogue, then select distinct feasible alternatives."""
    a = body.assumptions
    area = geometry["width_m"] * geometry["depth_m"]
    target = round(body.water_level_m + body.freeboard_m, 6)
    candidates = []
    materials = [
        ("standard", "Standard platform", a.standard_cost_m3, a.standard_carbon_kg_m3),
        ("lower-carbon", "Reduced-carbon mix", a.lower_carbon_cost_m3, a.lower_carbon_kg_m3),
    ]
    for lift_step in range(math.floor(body.max_raise_m * 10 + 1e-8) + 1):
        lift = lift_step / 10
        for material, label, cost_factor, carbon_factor in (materials if lift else [("none", "Existing design", 0, 0)]):
            for equipment_step in range(16 if body.allow_equipment_raise else 1):
                equipment_lift = equipment_step / 10
                volume = area * lift
                platform_cost = round(volume * cost_factor, 2)
                rack_cost = round(a.equipment_fixed_cost + equipment_lift * a.equipment_cost_m, 2) if equipment_lift else 0
                carbon = volume * carbon_factor + (a.equipment_fixed_carbon_kg + equipment_lift * a.equipment_carbon_kg_m if equipment_lift else 0)
                floor = round(body.baseline_floor_m + lift, 6)
                equipment = round(body.baseline_equipment_m + lift + equipment_lift, 6)
                protected_level = min(floor, equipment) if body.protect_floor else equipment
                clearance = round(protected_level - body.water_level_m, 6)
                candidates.append({
                    "id": f"{material}-{lift_step}-{equipment_step}", "material": material, "name": label,
                    "floor_raise_m": lift, "equipment_raise_m": equipment_lift,
                    "floor_m": floor, "equipment_m": equipment,
                    "volume_m3": round(volume, 3), "platform_cost_eur": platform_cost,
                    "equipment_cost_eur": rack_cost, "cost_eur": round(platform_cost + rack_cost, 2),
                    "added_carbon_kg": round(carbon, 2), "clearance_m": clearance,
                    "max_water_level_m": round(protected_level - body.freeboard_m, 6),
                    "floor_meets_target": floor + 1e-8 >= target,
                    "equipment_meets_target": equipment + 1e-8 >= target,
                    "meets_target": protected_level + 1e-8 >= target,
                    "badges": [],
                })
    meeting = [x for x in candidates if x["meets_target"]]
    affordable = [x for x in meeting if x["cost_eur"] <= body.budget_eur + 1e-8]
    cheapest = min(meeting, key=lambda x: (x["cost_eur"], x["added_carbon_kg"], -x["clearance_m"])) if meeting else None
    options = {}
    for badge, key in [
        ("Lowest cost", lambda x: (x["cost_eur"], x["added_carbon_kg"], -x["clearance_m"])),
        ("Lowest added carbon", lambda x: (x["added_carbon_kg"], x["cost_eur"], -x["clearance_m"])),
        ("Most clearance", lambda x: (-x["clearance_m"], x["cost_eur"], x["added_carbon_kg"])),
    ]:
        if affordable:
            chosen = min(affordable, key=key)
            if chosen["id"] not in options:
                options[chosen["id"]] = {**chosen, "badges": []}
            options[chosen["id"]]["badges"].append(badge)
    baseline_level = min(body.baseline_floor_m, body.baseline_equipment_m) if body.protect_floor else body.baseline_equipment_m
    baseline_clearance = round(baseline_level - body.water_level_m, 6)
    return {
        "version": "flood-options-1.0", "geometry_fingerprint": geometry_fingerprint(geometry),
        "status": "feasible" if affordable else "budget_shortfall" if meeting else "height_limit",
        "area_m2": round(area, 3), "target_elevation_m": target,
        "evaluated_count": len(candidates), "feasible_count": len(affordable),
        "baseline": {"floor_m": body.baseline_floor_m, "equipment_m": body.baseline_equipment_m,
                     "clearance_m": baseline_clearance, "meets_target": baseline_level + 1e-8 >= target},
        "required_floor_raise_m": max(0, math.ceil((target - body.baseline_floor_m - 1e-8) * 10) / 10) if body.protect_floor else 0,
        "minimum_budget_eur": cheapest["cost_eur"] if cheapest else None,
        "budget_gap_eur": round(max(0, cheapest["cost_eur"] - body.budget_eur), 2) if cheapest else None,
        "options": list(options.values()),
        "assumptions": [
            "User-selected water level; not a flood forecast. All elevations share one local ground datum.",
            "Solid platform volume = confirmed footprint area × added floor height. Existing equipment rises with the floor.",
            "Platform cost/carbon = volume × editable unit factors. Equipment mounting adds fixed and height-based allowances.",
            "Prices and carbon factors are illustrative demo assumptions, excluding access works, foundations, tax and site-specific engineering.",
            "Search uses 0.1 m increments, two platform mixes and up to 1.5 m of additional equipment lift.",
            "The test checks vertical clearance only. Drainage, structural loads, access, evacuation and utilities require separate review.",
        ],
    }
