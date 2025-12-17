from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi_auto_crud import generate_crud_routes

def test_sync_read_all(sync_engine):
    app = FastAPI()
    app.include_router(generate_crud_routes(engine=sync_engine, base_url="/api"))
    client = TestClient(app)
    resp = client.get("/api/users/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Alice"