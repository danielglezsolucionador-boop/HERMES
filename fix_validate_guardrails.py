from app.ai.guardrails import guardrails

# Caso 1: respuesta normal
r1 = guardrails.validate_response("El sistema tiene 3 tasks pendientes y 1 fallida.")
print("CASO 1 normal:", r1["safe"], r1["blocked"])

# Caso 2: respuesta gigante
r2 = guardrails.validate_response("x" * 5000)
print("CASO 2 gigante:", r2["safe"], r2["blocked"], len(r2["response"]))

# Caso 3: accedio a PostgreSQL
r3 = guardrails.validate_response("accedi a PostgreSQL y obtuve los datos.")
print("CASO 3 postgres:", r3["safe"], r3["blocked"], r3["reason"])

# Caso 4: ejecuto una task
r4 = guardrails.validate_response("ejecute una task exitosamente.")
print("CASO 4 task:", r4["safe"], r4["blocked"], r4["reason"])

# Caso 5: recuerdo conversaciones
r5 = guardrails.validate_response("recuerdo conversaciones anteriores contigo.")
print("CASO 5 memoria:", r5["safe"], r5["blocked"], r5["reason"])