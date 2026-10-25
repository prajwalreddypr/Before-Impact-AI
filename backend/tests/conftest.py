import os
import shutil
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///./test_beforeimpact.db"
os.environ["APP_ENV"] = "demo"
_TEST_UPLOADS = tempfile.mkdtemp(prefix="sustainbuild-tests-")
os.environ["UPLOAD_DIR"] = _TEST_UPLOADS

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app.seed import seed_demo


@pytest.fixture(scope="session", autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    seed_demo()
    yield
    Base.metadata.drop_all(engine)
    shutil.rmtree(_TEST_UPLOADS)


@pytest.fixture()
def client():
    with TestClient(app) as value:
        yield value


@pytest.fixture()
def auth(client):
    response = client.post("/api/auth/login", json={"email": "demo@beforeimpact.ai", "password": "Demo123!"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
