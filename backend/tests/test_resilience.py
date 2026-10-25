import math

import pytest
from pydantic import ValidationError

from app.resilience import ResilienceInput, solve


GEOMETRY = {"width_m": 42, "depth_m": 28, "floors": 2, "floor_height_m": 3.6, "building_type": "School", "zones": []}


def test_tradeoffs_have_checkable_quantities_and_distinct_objectives():
    result = solve(ResilienceInput(blueprint_id=1), GEOMETRY)
    assert result["status"] == "feasible"
    cheapest, lower_carbon, most_clearance = result["options"]
    assert cheapest["cost_eur"] == 190512  # 42 * 28 * 0.9 * EUR 180/m3
    assert cheapest["floor_m"] == 1.1
    assert cheapest["added_carbon_kg"] == 254016
    assert lower_carbon["cost_eur"] == 227556
    assert lower_carbon["added_carbon_kg"] == 137592
    assert most_clearance["floor_m"] == 1.6
    assert most_clearance["cost_eur"] <= 300000
    assert len({x["id"] for x in result["options"]}) == 3
    for option in result["options"]:
        assert option["floor_m"] >= 1.1
        assert option["equipment_m"] >= 1.1
        assert option["max_water_level_m"] == round(min(option["floor_m"], option["equipment_m"]) - .3, 2)


def test_budget_boundary_and_height_constraint_are_distinguished():
    exact = solve(ResilienceInput(blueprint_id=1, budget_eur=190512), GEOMETRY)
    assert exact["status"] == "feasible"
    below = solve(ResilienceInput(blueprint_id=1, budget_eur=190511), GEOMETRY)
    assert below["status"] == "budget_shortfall"
    assert below["options"] == []
    assert below["budget_gap_eur"] == 1
    locked = solve(ResilienceInput(blueprint_id=1, budget_eur=10000000, max_raise_m=.89), GEOMETRY)
    assert locked["status"] == "height_limit"
    assert locked["minimum_budget_eur"] is None
    assert locked["required_floor_raise_m"] == .9


def test_equipment_only_has_a_real_tradeoff_and_honest_floor_status():
    result = solve(ResilienceInput(blueprint_id=1, protect_floor=False, max_raise_m=0, budget_eur=3500), GEOMETRY)
    cheapest = result["options"][0]
    assert cheapest["cost_eur"] == 3420
    assert cheapest["equipment_m"] == 1.1
    assert cheapest["floor_m"] == .2
    assert cheapest["equipment_meets_target"] is True
    assert cheapest["floor_meets_target"] is False
    locked = solve(ResilienceInput(blueprint_id=1, protect_floor=False, max_raise_m=0, allow_equipment_raise=False), GEOMETRY)
    assert locked["status"] == "height_limit"


def test_no_work_is_recommended_as_cheapest_when_baseline_meets_target():
    result = solve(ResilienceInput(blueprint_id=1, water_level_m=0, freeboard_m=.2, budget_eur=0), GEOMETRY)
    assert result["baseline"]["meets_target"] is True
    assert len(result["options"]) == 1
    assert result["options"][0]["cost_eur"] == 0
    assert result["options"][0]["floor_raise_m"] == 0


def test_display_rounding_does_not_turn_a_missed_target_into_a_pass():
    result = solve(ResilienceInput(blueprint_id=1, water_level_m=0, freeboard_m=.2,
                                  baseline_floor_m=.199, budget_eur=0), GEOMETRY)
    assert result["baseline"]["meets_target"] is False
    assert result["status"] == "budget_shortfall"


@pytest.mark.parametrize("patch", [{"budget_eur": -1}, {"water_level_m": math.inf}, {"max_raise_m": 3.1}, {"baseline_floor_m": 1, "baseline_equipment_m": .3}])
def test_invalid_constraints_are_rejected(patch):
    with pytest.raises(ValidationError):
        ResilienceInput(blueprint_id=1, **patch)


@pytest.fixture()
def planning_context(client, auth):
    f = client.post("/api/facilities", headers=auth, json={"name":"Resilience test school", "facility_type":"school", "industry":"test", "country":"France", "address_label":"Test", "latitude":45, "longitude":4}).json()
    bp = client.post(f"/api/facilities/{f['id']}/blueprints/demo?plan_type=school", headers=auth).json()
    client.put(f"/api/blueprints/{bp['id']}/geometry", headers=auth, json=GEOMETRY).raise_for_status()
    project = client.post("/api/construction-projects", headers=auth, json={"name":"Resilience test", "data":{"facility_id":f["id"], "blueprint":{"id":bp["id"]}, "unrelated_field":"preserved"}}).json()
    return project["id"], bp["id"]


def test_comparison_apply_reload_and_report(client, auth, planning_context):
    project_id, bp_id = planning_context
    url = f"/api/construction-projects/{project_id}"
    comparison = client.post(url+"/resilience/solve", headers=auth, json={"blueprint_id":bp_id})
    assert comparison.status_code == 200
    data = comparison.json()["data"]
    study = data["resilience"]
    assert data["unrelated_field"] == "preserved"
    assert "resilience_applied" not in data
    option = study["result"]["options"][0]
    applied = client.post(url+"/resilience/apply", headers=auth, json={"study_id":study["id"], "option_id":option["id"]})
    assert applied.status_code == 200
    reloaded = client.get(url, headers=auth).json()["data"]
    assert reloaded["adaptations"]["finished_floor_m"] == 1.1
    assert reloaded["resilience"]["applied_option_id"] == option["id"]
    assert reloaded["resilience_applied"]["option"]["cost_eur"] == 190512
    report = client.post(url+"/report", headers=auth)
    assert report.status_code == 200
    assert client.get(f"/api/reports/{report.json()['id']}/download", headers=auth).content.startswith(b"%PDF")
    # A new comparison does not silently apply a different design.
    changed = client.post(url+"/resilience/solve", headers=auth, json={"blueprint_id":bp_id, "budget_eur":0}).json()["data"]
    assert changed["resilience"]["result"]["status"] == "budget_shortfall"
    assert changed["adaptations"]["finished_floor_m"] == 1.1
    assert client.post(url+"/resilience/apply", headers=auth, json={"study_id":study["id"], "option_id":option["id"]}).status_code == 409


def test_changed_geometry_and_infeasible_options_cannot_be_applied(client, auth, planning_context):
    project_id, bp_id = planning_context
    url = f"/api/construction-projects/{project_id}"
    study = client.post(url+"/resilience/solve", headers=auth, json={"blueprint_id":bp_id}).json()["data"]["resilience"]
    body = {"study_id":study["id"], "option_id":study["result"]["options"][0]["id"]}
    assert client.post(url+"/resilience/apply", headers=auth, json={**body, "option_id":"made-up"}).status_code == 422
    client.put(f"/api/blueprints/{bp_id}/geometry", headers=auth, json={**GEOMETRY, "width_m":50})
    assert client.post(url+"/resilience/apply", headers=auth, json=body).status_code == 409


def test_confirmation_ownership_and_project_link_are_enforced(client, auth, planning_context):
    from app.db import SessionLocal
    from app.models import User
    from app.main import token_for
    from app.seed import password_hash
    project_id, bp_id = planning_context
    url = f"/api/construction-projects/{project_id}/resilience/solve"
    assert client.post(url, json={"blueprint_id":bp_id}).status_code == 401
    with SessionLocal() as db:
        other = User(email="resilience-review@example.test", display_name="Test", password_hash=password_hash("test"))
        db.add(other); db.commit(); db.refresh(other)
        other_auth = {"Authorization":f"Bearer {token_for(other)}"}
        try:
            assert client.post(url, headers=other_auth, json={"blueprint_id":bp_id}).status_code == 404
            other_project = client.post("/api/construction-projects", headers=other_auth, json={"name":"Other user's project", "data":{"blueprint":{"id":bp_id}}}).json()
            assert client.post(f"/api/construction-projects/{other_project['id']}/resilience/solve", headers=other_auth, json={"blueprint_id":bp_id}).status_code == 404
        finally:
            db.delete(other); db.commit()
    client.patch(f"/api/construction-projects/{project_id}", headers=auth, json={"data":{}})
    assert client.post(url, headers=auth, json={"blueprint_id":bp_id}).status_code == 422


def test_apply_recalculates_instead_of_trusting_stored_prices(client, auth, planning_context):
    project_id, bp_id = planning_context
    url = f"/api/construction-projects/{project_id}"
    data = client.post(url+"/resilience/solve", headers=auth, json={"blueprint_id":bp_id}).json()["data"]
    study = data["resilience"]
    option = study["result"]["options"][0]
    option["cost_eur"] = 0
    client.patch(url, headers=auth, json={"data":data})
    applied = client.post(url+"/resilience/apply", headers=auth, json={"study_id":study["id"], "option_id":option["id"]})
    assert applied.json()["data"]["resilience_applied"]["option"]["cost_eur"] == 190512


def test_unconfirmed_blueprint_cannot_be_used(client, auth, planning_context):
    project_id, bp_id = planning_context
    project_url = f"/api/construction-projects/{project_id}"
    data = client.get(project_url, headers=auth).json()["data"]
    unconfirmed = client.post(f"/api/facilities/{data['facility_id']}/blueprints/demo", headers=auth).json()
    client.patch(project_url, headers=auth, json={"data":{**data, "blueprint":{"id":unconfirmed["id"]}}})
    response = client.post(project_url+"/resilience/solve", headers=auth, json={"blueprint_id":unconfirmed["id"]})
    assert response.status_code == 422
    assert "Confirm blueprint geometry" in response.json()["detail"]
