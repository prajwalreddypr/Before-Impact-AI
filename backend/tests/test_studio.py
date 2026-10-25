import copy
import json

import httpx
import pytest

from app.resilience import ResilienceInput, solve
from app.studio import BriefRequest, StressRequest, local_brief, parse_brief, search_addresses, site_evidence, stress_test
from test_resilience import GEOMETRY, planning_context


ADDRESS = {"id": "69123", "label": "Lyon", "citycode": "69123", "latitude": 45.758, "longitude": 4.835, "precision": "municipality"}


@pytest.mark.parametrize("text, expected", [
    ("Budget €250,000. Flood 0.8 m, freeboard 30 cm, maximum floor raise 1.5 m. Protect floor and equipment.",
     {"budget_eur": 250000, "water_level_m": .8, "freeboard_m": .3, "max_raise_m": 1.5, "protect_floor": True}),
    ("Budget €5k. 80 cm flood. Equipment only. Maximum floor raise 0 m.",
     {"budget_eur": 5000, "water_level_m": .8, "max_raise_m": 0, "protect_floor": False}),
    ("Budget 1.2 million euros. No additional equipment lift.",
     {"budget_eur": 1200000, "allow_equipment_raise": False}),
    ("A beautiful sustainable school in Lyon for 600 students", {}),
])
def test_local_brief_extracts_only_explicit_supported_fields(text, expected):
    assert local_brief(text) == expected


def test_brief_preserves_custom_assumptions_and_missing_values(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    current = ResilienceInput(blueprint_id=7, water_level_m=1.2, assumptions={"standard_cost_m3": 225})
    parsed = parse_brief(BriefRequest(text="Budget €260k", current=current, use_ai=True))
    assert parsed["mode"] == "local_parser"
    assert parsed["input"]["budget_eur"] == 260000
    assert parsed["input"]["water_level_m"] == 1.2
    assert parsed["input"]["assumptions"]["standard_cost_m3"] == 225
    assert parsed["input"]["blueprint_id"] == 7
    assert parsed["extracted"] == ["budget_eur"]


def test_ai_structured_output_and_unavailable_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    def fake_post(url, **kwargs):
        assert url == "https://api.openai.com/v1/responses"
        assert kwargs["json"]["text"]["format"]["strict"] is True
        fields = {"budget_eur": 150000, "water_level_m": None, "freeboard_m": None,
                  "max_raise_m": None, "protect_floor": None, "allow_equipment_raise": None}
        return httpx.Response(200, request=httpx.Request("POST", url), json={"output":[{"content":[{"type":"output_text", "text":json.dumps(fields)}]}]})
    monkeypatch.setattr("app.studio.httpx.post", fake_post)
    body = BriefRequest(text="Budget €150k", current=ResilienceInput(blueprint_id=1), use_ai=True)
    assert parse_brief(body)["mode"] == "ai_parser"
    def unavailable(*args, **kwargs):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr("app.studio.httpx.post", unavailable)
    result = parse_brief(body)
    assert result["mode"] == "local_parser"
    assert result["input"]["budget_eur"] == 150000


def test_brief_endpoint_bounds_and_auth(client, auth):
    body = {"text": "Budget €250k", "current": {"blueprint_id": 1}}
    assert client.post("/api/studio/brief", json=body).status_code == 401
    assert client.post("/api/studio/brief", headers=auth, json=body).json()["input"]["budget_eur"] == 250000
    body["text"] = "Flood 6 m"
    assert client.post("/api/studio/brief", headers=auth, json=body).status_code == 422


def test_official_provider_shapes_sources_and_missing_coverage(monkeypatch):
    def fake_get(url, **kwargs):
        if "geocodage" in url:
            assert kwargs["params"]["q"] == "Lyon"
            data = {"features":[{"properties":{"id":"69123","label":"Lyon","citycode":"69123","type":"municipality"},"geometry":{"coordinates":[4.835,45.758]}}]}
        else:
            assert "code_insee=69123" in url
            data = {"response_code":200,"data":[{"code_insee":"69123","risques_detail":[{"libelle_risque_long":"Inondation"},{"libelle_risque_long":"Inondation"}]},
                                                 {"code_insee":"75056","risques_detail":[{"libelle_risque_long":"Ignore other municipality"}]}]}
        return httpx.Response(200, request=httpx.Request("GET",url), json=data)
    monkeypatch.setattr("app.studio.httpx.get", fake_get)
    address = search_addresses("Lyon")["addresses"][0]
    assert address == ADDRESS
    evidence = site_evidence(address)
    assert evidence["status"] == "available"
    assert evidence["risks"] == ["Inondation"]
    assert evidence["retrieved_at"] and "Municipality" in evidence["scope"]
    def offline(*args, **kwargs):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr("app.studio.httpx.get", offline)
    assert site_evidence(address)["status"] == "unavailable"
    monkeypatch.setattr("app.studio.httpx.get", lambda url, **kwargs: httpx.Response(200, request=httpx.Request("GET",url), json={"response_code":200,"data":[]}))
    assert site_evidence(address)["status"] == "no_record"


@pytest.fixture()
def saved_design(client, auth, planning_context):
    project_id, bp_id = planning_context
    root = f"/api/construction-projects/{project_id}"
    study = client.post(root+"/resilience/solve", headers=auth, json={"blueprint_id": bp_id}).json()["data"]["resilience"]
    body = {"name":"School first proposal", "study_id":study["id"], "option_id":study["result"]["options"][0]["id"]}
    response = client.post(root+"/studio/designs", headers=auth, json=body)
    assert response.status_code == 200
    return root, response.json()["data"]["design_library"][0], body


def test_archive_roundtrip_new_comparison_restore_and_delete(client, auth, saved_design):
    root, design, body = saved_design
    assert design["option"]["cost_eur"] == 190512
    assert design["geometry"] == GEOMETRY
    client.post(root+"/resilience/solve", headers=auth, json={"blueprint_id":design["input"]["blueprint_id"],"budget_eur":1000})
    data = client.get(root,headers=auth).json()["data"]
    assert data["design_library"][0] == design
    assert data["unrelated_field"] == "preserved"
    assert client.post(root+"/studio/designs",headers=auth,json=body).status_code == 409
    restored = client.post(root+f"/studio/designs/{design['id']}/restore",headers=auth)
    assert restored.status_code == 200
    restored_data = restored.json()["data"]
    assert restored_data["resilience"]["id"] != body["study_id"]
    assert restored_data["resilience"]["input"]["budget_eur"] == 300000
    assert restored_data["resilience"]["applied_option_id"] is None
    assert "resilience_applied" not in restored_data
    deleted = client.delete(root+f"/studio/designs/{design['id']}",headers=auth)
    assert deleted.json()["data"]["design_library"] == []


def test_archive_recalculates_tampered_prices_and_rejects_unknown_option(client, auth, saved_design):
    root, design, body = saved_design
    data = client.get(root,headers=auth).json()["data"]
    data["resilience"]["result"]["options"][0]["cost_eur"] = 1
    client.patch(root,headers=auth,json={"data":data})
    result = client.post(root+"/studio/designs",headers=auth,json=body)
    assert result.json()["data"]["design_library"][-1]["option"]["cost_eur"] == 190512
    assert client.post(root+"/studio/designs",headers=auth,json={**body,"option_id":"invented"}).status_code == 422


def test_stress_boundaries_cost_escalation_and_equipment_only():
    inputs = ResilienceInput(blueprint_id=1, budget_eur=190512)
    option = solve(inputs, GEOMETRY)["options"][0]
    design = {"id":"test", "input":inputs.model_dump(), "geometry":GEOMETRY, "option":option}
    grid = stress_test(design, StressRequest(water_levels=[.8,.8001],cost_increases_pct=[0,.01]))
    assert [c["reason"] for c in grid["cells"]] == ["Meets both","Budget","Water clearance","Water + budget"]
    assert grid["max_cost_increase_pct"] == 0
    inputs = ResilienceInput(blueprint_id=1, protect_floor=False, max_raise_m=0, budget_eur=3500)
    design.update(input=inputs.model_dump(), option=solve(inputs,GEOMETRY)["options"][0])
    grid = stress_test(design,StressRequest(water_levels=[.8],cost_increases_pct=[0]))
    assert grid["passing_count"] == 1
    assert grid["protect_floor"] is False
    assert grid["option"]["floor_meets_target"] is False


def test_zero_cost_design_does_not_divide_by_zero():
    inputs = ResilienceInput(blueprint_id=1,water_level_m=0,freeboard_m=.2,budget_eur=0)
    option = solve(inputs, GEOMETRY)["options"][0]
    design = {"id":"test", "input":inputs.model_dump(), "geometry":GEOMETRY, "option":option}
    assert stress_test(design,StressRequest())["max_cost_increase_pct"] is None


def test_stress_endpoint_invalid_ranges_stale_geometry_and_ownership(client, auth, saved_design):
    root, design, _ = saved_design
    route = root+f"/studio/designs/{design['id']}"
    tested = client.post(route+"/stress", headers=auth,json={})
    assert tested.status_code == 200
    persisted = client.get(root,headers=auth).json()["data"]["design_library"][0]["last_stress"]
    assert persisted["tested_at"] == tested.json()["tested_at"]
    assert persisted["cells"] == tested.json()["cells"]
    assert client.post(route+"/stress", headers=auth,json={"water_levels":[6]}).status_code == 422
    assert client.post(route+"/stress", headers=auth,json={"water_levels":[]}).status_code == 422
    assert client.post(route+"/stress",json={}).status_code == 401
    bp_id = design["input"]["blueprint_id"]
    client.put(f"/api/blueprints/{bp_id}/geometry",headers=auth,json={**GEOMETRY,"width_m":50}).raise_for_status()
    assert client.post(route+"/restore",headers=auth).status_code == 409
    # Historical stress testing still uses the saved footprint, not today's edited one.
    historical = client.post(route+"/stress",headers=auth,json={}).json()
    assert historical["option"]["cost_eur"] == 190512


def test_site_evidence_snapshot_does_not_change_with_current_site(client, auth, saved_design, monkeypatch):
    root, design, body = saved_design
    monkeypatch.setattr("app.studio.search_addresses", lambda query:{"addresses":[ADDRESS]})
    original = {"address":ADDRESS,"retrieved_at":"2026-10-25T00:00:00Z","status":"available","risks":["Inondation"],"scope":"Municipality","address_source":"https://data.geopf.fr/geocodage/search","risk_source":"https://www.georisques.gouv.fr/api/v1/gaspar/risques?code_insee=69123"}
    monkeypatch.setattr("app.studio.site_evidence", lambda address:copy.deepcopy(original))
    attached = client.post(root+"/studio/site",headers=auth,json={"query":"Lyon","address_id":"69123"})
    assert attached.status_code == 200
    assert attached.json()["data"]["design_library"][0]["site_evidence"] is None
    new = client.post(root+"/studio/designs",headers=auth,json=body).json()["data"]["design_library"][-1]
    assert new["site_evidence"] == original
    assert client.post(root+"/studio/site",headers=auth,json={"query":"Lyon","address_id":"missing"}).status_code == 409


def test_other_owner_cannot_read_or_mutate_studio(client, auth, saved_design):
    from app.db import SessionLocal
    from app.models import User
    from app.seed import password_hash
    with SessionLocal() as db:
        user = User(email="studio-other@example.test",display_name="Other",password_hash=password_hash("test-password"))
        db.add(user);db.commit()
    token = client.post("/api/auth/login",json={"email":"studio-other@example.test","password":"test-password"}).json()["access_token"]
    other = {"Authorization":f"Bearer {token}"}
    root, design, body = saved_design
    for path, payload in [("/studio/designs",body),(f"/studio/designs/{design['id']}/restore",{}),(f"/studio/designs/{design['id']}/stress",{}),("/studio/site",{"query":"Lyon","address_id":"69123"})]:
        assert client.post(root+path,headers=other,json=payload).status_code == 404
    assert client.delete(root+f"/studio/designs/{design['id']}",headers=other).status_code == 404
