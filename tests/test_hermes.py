import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ─── SISTEMA ───

@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_status(client):
    r = await client.get("/status")
    assert r.status_code == 200
    assert r.json()["database"] == "connected"


@pytest.mark.asyncio
async def test_ready(client):
    r = await client.get("/ready")
    assert r.status_code in (200, 503)


# ─── CRUD ───

@pytest.mark.asyncio
async def test_create_task(client):
    r = await client.post("/tasks", json={"name": "test-create"})
    assert r.status_code == 201
    assert r.json()["status"] == "pending"
    assert "id" in r.json()


@pytest.mark.asyncio
async def test_list_tasks(client):
    await client.post("/tasks", json={"name": "list-test"})
    r = await client.get("/tasks")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_tasks_pagination(client):
    r = await client.get("/tasks?limit=2&offset=0")
    assert r.status_code == 200
    assert len(r.json()) <= 2


@pytest.mark.asyncio
async def test_get_task(client):
    r_create = await client.post("/tasks", json={"name": "get-test"})
    task_id = r_create.json()["id"]
    r = await client.get(f"/tasks/{task_id}")
    assert r.status_code == 200
    assert r.json()["id"] == task_id


@pytest.mark.asyncio
async def test_update_task_status(client):
    r_create = await client.post("/tasks", json={"name": "update-test"})
    task_id = r_create.json()["id"]
    r = await client.patch(f"/tasks/{task_id}", json={"status": "running"})
    assert r.status_code == 200
    assert r.json()["status"] == "running"


@pytest.mark.asyncio
async def test_delete_task(client):
    r_create = await client.post("/tasks", json={"name": "delete-test"})
    task_id = r_create.json()["id"]
    r = await client.delete(f"/tasks/{task_id}")
    assert r.status_code == 204


# ─── ERRORES ───

@pytest.mark.asyncio
async def test_invalid_uuid(client):
    r = await client.get("/tasks/uuid-invalido-xyz")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_task_not_found(client):
    r = await client.get("/tasks/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_not_found(client):
    r = await client.delete("/tasks/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404