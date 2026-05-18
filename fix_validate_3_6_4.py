import asyncio
from app.ai.orchestrator import orchestrator

async def main():
    # Test 1 — API key ausente -> error controlado
    result = await orchestrator.generate("Dame el estado operacional actual")
    print('OK Test 1 — API key ausente')
    print('  success     :', result['success'])
    print('  error       :', result['error'])
    print('  response    :', result['response'])
    print('  duration_ms :', result['duration_ms'])
    assert result['success'] == False, 'FAIL — debe ser False'
    assert result['error'] is not None, 'FAIL — debe tener error'
    assert result['response'] is None, 'FAIL — response debe ser None'
    print('TODOS LOS TESTS OK')

asyncio.run(main())