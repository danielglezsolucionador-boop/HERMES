from app.ai.context_isolation import redact_secrets, truncate_safe, build_operational_context

# Test 1 — redaccion secretos
text = 'key=sk-ant-abcdefghij1234567890 url=postgresql+asyncpg://user:pass@host/db'
redacted, count = redact_secrets(text)
assert 'sk-ant-****' in redacted, 'FAIL redact sk-ant'
assert 'postgresql+asyncpg://****' in redacted, 'FAIL redact db url'
assert count >= 2, 'FAIL redaction count'
print('OK Test 1 — redaccion secretos count=' + str(count))

# Test 2 — truncado
big = 'A' * 10000
truncated, was_truncated = truncate_safe(big)
assert was_truncated, 'FAIL truncado'
assert len(truncated) < 10000, 'FAIL largo'
print('OK Test 2 — truncado len=' + str(len(truncated)))

# Test 3 — contexto vacio
ctx = build_operational_context()
assert ctx['tasks'] == [], 'FAIL tasks vacio'
assert '_isolation' in ctx, 'FAIL isolation key'
print('OK Test 3 — contexto vacio')

# Test 4 — context con tasks
tasks = [{'id': '1', 'title': 'Test', 'description': 'Desc', 'status': 'done', 'error': None, 'retry_count': 0}]
ctx = build_operational_context(tasks=tasks, summary='resumen operacional')
assert len(ctx['tasks']) == 1, 'FAIL tasks count'
assert ctx['summary'] == 'resumen operacional', 'FAIL summary'
print('OK Test 4 — context con tasks')

print('TODOS LOS TESTS OK')