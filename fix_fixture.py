content = open('tests/test_hermes.py', 'r', encoding='utf-8').read()

old = '''@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac'''

new = ''

assert old in content, 'BLOQUE NO ENCONTRADO'
content = content.replace(old, new)

# Limpiar imports que ya no se necesitan en test_hermes.py
content = content.replace('from httpx import AsyncClient, ASGITransport\n', '')
content = content.replace('from app.main import app\n', '')

open('tests/test_hermes.py', 'w', encoding='utf-8').write(content)
print('OK - fixture removido de test_hermes.py')