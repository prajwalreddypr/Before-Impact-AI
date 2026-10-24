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


def test_plan_persistence_and_scenario_difference(client, auth):
    facility = client.get("/api/facilities", headers=auth).json()[0]
    event = client.get(f"/api/facilities/{facility['id']}/events", headers=auth).json()[0]
    plan = client.post(f"/api/events/{event['id']}/generate-plan", headers=auth).json()
    first = plan["items"][0]
    updated = client.patch(f"/api/plans/{plan['id']}/items/{first['id']}", headers=auth, json={"status":"completed","user_notes":"test"})
    assert updated.json()["status"] == "completed"
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
