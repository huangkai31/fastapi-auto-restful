import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from fastapi_auto_restful import generate_crud_routes

@pytest.mark.asyncio
async def test_async_create(async_engine):
    app = FastAPI()
    app.include_router(generate_crud_routes(engine=async_engine, base_url="/api"))
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post("/api/users/", json={"name": "Bob", "email": "bob@test.com"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "Bob"