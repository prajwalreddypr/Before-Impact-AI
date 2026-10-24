from io import BytesIO


def test_authentication(client, auth):
    assert client.get("/api/auth/me", headers=auth).json()["email"] == "demo@beforeimpact.ai"
    assert client.post("/api/auth/login", json={"email": "demo@beforeimpact.ai", "password": "wrong"}).status_code == 401


def test_facilities_and_ownership(client, auth):
    rows = client.get("/api/facilities", headers=auth).json()
    assert len(rows) >= 6
    created = client.post("/api/facilities", headers=auth, json={"name":"Test site","facility_type":"warehouse","industry":"Logistics","country":"France","address_label":"Test","latitude":45,"longitude":4,"timezone":"UTC","currency":"EUR","status":"proposed"})
    assert created.status_code == 200
    assert client.get("/api/facilities/99999", headers=auth).status_code == 404


def test_timeline_is_ordered(client, auth):
    facility = client.get("/api/facilities", headers=auth).json()[0]
    event = client.get(f"/api/facilities/{facility['id']}/events", headers=auth).json()[0]
    payload = client.get(f"/api/events/{event['id']}/timeline", headers=auth).json()
    timestamps = [x["timestamp"] for x in payload["readings"]]
    assert len(timestamps) == 49
    assert timestamps == sorted(timestamps)
    assert payload["source"]["synthetic"] is True


def test_portfolio_has_six_major_hazards(client, auth):
    payload = client.get("/api/warnings", headers=auth)
    assert payload.status_code == 200
    warnings = payload.json()["warnings"]
    assert {x["hazard_type"] for x in warnings} == {"wind", "flood", "rain", "heat", "wildfire", "drought"}
    assert all(x["is_synthetic"] for x in warnings)


def test_new_construction_flow(client, auth):
    presets = client.get("/api/site-presets", headers=auth).json()["locations"]
    assert len(presets) == 13
    tokyo = next(x for x in presets if x["id"] == "tokyo-bay")
    site = client.post("/api/facilities", headers=auth, json={"name":"Tokyo test factory","facility_type":"factory","industry":"Construction planning","country":"Japan","address_label":"Tokyo Bay","latitude":tokyo["latitude"],"longitude":tokyo["longitude"],"timezone":"Asia/Tokyo","currency":"JPY","status":"proposed"}).json()
    blueprint = client.post(f"/api/facilities/{site['id']}/blueprints/demo", headers=auth)
    assert blueprint.status_code == 200
    model = client.post(f"/api/blueprints/{blueprint.json()['id']}/generate-model", headers=auth).json()
    assert model["conceptual"] is True and len(model["blocks"]) >= 3
    evaluation = client.post("/api/sites/evaluate", headers=auth, json={"preset_id":"tokyo-bay","facility_type":"Factory","roof_area_m2":model["roof_area_m2"],"simulations":{"rain":85,"wind":70}})
    assert evaluation.status_code == 200
    assert evaluation.json()["rainwater"]["annual_capture_potential_m3"] > 0


def test_persistent_project_search_adaptation_and_sustainability(client, auth):
    project = client.post("/api/construction-projects", headers=auth, json={"name":"Japan school demo","building_type":"School","region":"Japan","entry_mode":"find","selected_site_ids":[],"data":{"requirements":{"land":5000}}})
    assert project.status_code == 200
    project_id = project.json()["id"]
    search = client.post("/api/candidate-sites/search", headers=auth, json={"building_type":"School","region":"Japan","minimum_land_area_m2":5000,"building_area_m2":1800,"floors":2,"priority":"balanced"}).json()
    assert len(search["sites"]) == 8 and "weights" in search
    france = client.post("/api/candidate-sites/search", headers=auth, json={"building_type":"School","region":"France","minimum_land_area_m2":5000,"building_area_m2":1800,"floors":2,"priority":"balanced"}).json()
    assert len(france["sites"]) == 5 and all(x["country"] == "France" for x in france["sites"])
    selected = [search["sites"][0]["id"], search["sites"][1]["id"]]
    saved = client.patch(f"/api/construction-projects/{project_id}", headers=auth, json={"selected_site_ids":selected,"active_section":"intelligence"})
    assert saved.json()["selected_site_ids"] == selected
    flood = client.post("/api/simulations/run", headers=auth, json={"site_id":selected[0],"hazard":"flood","intensity":0.8,"baseline_floor_m":0.2,"finished_floor_m":1.0})
    assert flood.json()["before"]["intersects"] is True
    assert flood.json()["after"]["intersects"] is False
    sustainability = client.post("/api/sustainability/calculate", headers=auth, json={"site_id":selected[0],"roof_area_m2":1200,"collection_efficiency":0.8,"storage_m3":200,"concrete_t":1000,"steel_t":150,"timber_t":50,"insulation_t":20})
    assert sustainability.json()["rainwater"]["annual_potential_m3"] > 0
    report = client.post(f"/api/construction-projects/{project_id}/report", headers=auth)
    assert report.status_code == 200
    assert client.get(f"/api/reports/{report.json()['id']}/download", headers=auth).content.startswith(b"%PDF")


def test_plan_persistence_and_scenario_difference(client, auth):
    facility = client.get("/api/facilities", headers=auth).json()[0]
    event = client.get(f"/api/facilities/{facility['id']}/events", headers=auth).json()[0]
    plan = client.post(f"/api/events/{event['id']}/generate-plan", headers=auth).json()
    first = plan["items"][0]
    updated = client.patch(f"/api/plans/{plan['id']}/items/{first['id']}", headers=auth, json={"status":"completed","user_notes":"test","assignee_name":"Site lead"})
    assert updated.json()["status"] == "completed"
    assert updated.json()["assignee_name"] == "Site lead"
    base = client.post("/api/scenarios", headers=auth, json={"facility_id":facility["id"],"weather_event_id":event["id"],"name":"No prep test","scenario_type":"unprepared","selected_action_ids":[]}).json()
    prepared = client.post("/api/scenarios", headers=auth, json={"facility_id":facility["id"],"weather_event_id":event["id"],"name":"Prepared test","scenario_type":"prepared","selected_action_ids":[first["action"]["id"], plan["items"][1]["action"]["id"]]}).json()
    assert prepared["result"]["exposure_score"] < base["result"]["exposure_score"]
    compare = client.post("/api/scenarios/compare", headers=auth, json={"scenario_a_id":base["id"],"scenario_b_id":prepared["id"]}).json()
    assert compare["difference"]["exposure_points"] > 0


def test_blueprint_validation(client, auth):
    facility = client.get("/api/facilities", headers=auth).json()[0]
    response = client.post(f"/api/facilities/{facility['id']}/blueprints", headers=auth, files={"file":("unsafe.exe", BytesIO(b"not executable"), "application/octet-stream")})
    assert response.status_code == 415


def test_report_generation(client, auth):
    facility = client.get("/api/facilities", headers=auth).json()[0]
    response = client.post("/api/reports", headers=auth, json={"facility_id":facility["id"],"title":"Test resilience report","report_type":"scenario_summary"})
    assert response.status_code == 200
    download = client.get(f"/api/reports/{response.json()['id']}/download", headers=auth)
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF")


def test_seed_is_idempotent():
    from app.seed import seed_demo
    from app.db import SessionLocal
    from app.models import User
    from sqlalchemy import func, select
    seed_demo(); seed_demo()
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
