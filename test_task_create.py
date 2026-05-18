import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

async def main():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Test 1: crear task básica
        r = await client.post("/tasks", json={
            "title": "Revisar arquitectura Hermes",
            "description": "Validar que todos los modulos esten operacionales",
            "phase": "arquitectura"
        })
        print(f"Status: {r.status_code}")
        data = r.json()
        print(f"ID: {data['id']}")
        print(f"Title: {data['title']}")
        print(f"Status: {data['status']}")
        print(f"Phase: {data['phase']}")
        print(f"Description: {data['description']}")
        assert r.status_code == 201
        assert data['status'] == 'pending'
        assert data['title'] == 'Revisar arquitectura Hermes'
        print("\nTest 1 OK - task creada correctamente")

        # Test 2: crear segunda task
        r2 = await client.post("/tasks", json={
            "title": "Validar persistencia mensajes",
            "phase": "validacion"
        })
        assert r2.status_code == 201
        print("Test 2 OK - segunda task creada")

        # Test 3: listar tasks
        r3 = await client.get("/tasks")
        assert r3.status_code == 200
        tasks = r3.json()
        assert isinstance(tasks, list)
        print(f"Test 3 OK - {len(tasks)} tasks listadas")

        print("\nSubfase 3.1 VALIDADA")

asyncio.run(main())