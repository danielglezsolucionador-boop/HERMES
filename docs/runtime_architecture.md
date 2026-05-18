# HERMES — Runtime Architecture
**Fuente oficial de verdad arquitectónica.**
Este documento NO es decorativo. Es la referencia obligatoria antes de implementar cualquier runner, executor, concurrencia, u orchestration.

---

## 1. Filosofía Runtime-First

Hermes se construye **runtime-first**, no LLM-first.

El objetivo no es una demo de IA impresionante. El objetivo es un **kernel operacional robusto** que pueda ejecutar trabajo real de forma consistente, observable, recuperable y persistente.

Un sistema que no puede sobrevivir un error no merece escalar.

---

## 2. Arquitectura Oficial
Task → Runner → Executor → PostgreSQL
**Un solo flujo. Una sola verdad.**

- La Task existe en PostgreSQL con un status claro.
- El Runner toma la Task y la entrega al Executor.
- El Executor ejecuta y persiste el resultado.
- PostgreSQL es la única fuente de verdad del estado.

No hay estado en memoria que no esté respaldado por PostgreSQL.

---

## 3. Orden Correcto de Crecimiento
Consistencia operacional
Observabilidad
Recovery
Persistencia correcta
Escalamiento


**NUNCA al revés.**

No se escala lo que no es consistente.
No se distribuye lo que no sobrevive errores.
No se paraleliza lo que no tiene recovery.

---

## 4. Restricciones Actuales — Prohibido Implementar

Hasta validar estabilidad operacional completa, está **prohibido** implementar:

- Multiworker
- Paralelismo complejo
- Redis queues
- Celery
- Kafka
- Orchestration distribuida
- Auto-scaling
- Clusters
- Workers remotos
- Concurrencia avanzada

**Razón:** Todavía se está validando consistencia operacional en un solo proceso.

---

## 5. Qué Debe Demostrarse Primero

Antes de cualquier escala, Hermes debe demostrar:

- ✅ 1 proceso estable
- ✅ 1 runner estable
- ✅ 1 loop estable
- ✅ 1 flujo consistente
- ✅ 1 verdad operacional (PostgreSQL)
- ✅ Recovery correcto ante errores
- ✅ Persistencia correcta de estados
- ✅ Restart correcto sin pérdida de estado
- ✅ Logs correctos y observables
- ✅ Errores controlados y manejados

---

## 6. Reglas de Consistencia Operacional

- El status de una Task en PostgreSQL es la **única fuente de verdad**.
- Ningún runner asume el estado de una Task sin leerlo de la DB.
- Si un runner muere, la Task queda en su último estado persistido.
- No existe "estado en vuelo" que no esté en PostgreSQL.
- Antes de ejecutar: leer estado. Después de ejecutar: persistir resultado.

---

## 7. Recovery Philosophy

- El runner debe sobrevivir excepciones sin crashear el proceso principal.
- Una Task fallida se marca `failed` con `error` descriptivo en PostgreSQL.
- El sistema debe poder reiniciarse y retomar desde el estado persistido.
- No se pierde trabajo por un restart limpio.
- Recovery no es opcional — es parte del contrato del runner.

---

## 8. Observability Philosophy

- Cada transición de estado de una Task debe loggearse.
- El runner loggea: inicio, progreso, resultado, error.
- Los logs son la primera herramienta de diagnóstico.
- Sin observabilidad, no hay debugging. Sin debugging, no hay estabilidad.
- Formato de log: `timestamp | level | module | mensaje estructurado`

---

## 9. Regla de Oro del Runner

Un runner que no cumple estas condiciones **no se pone en producción**:

1. Sobrevive excepciones sin crashear
2. Persiste el resultado (éxito o error) en PostgreSQL
3. Mantiene consistencia de estado ante cualquier fallo
4. Loggea todas las transiciones
5. Puede reiniciarse sin corrupción de estado

---

## 10. Estrategia Futura de Escalamiento

Cuando la estabilidad operacional esté demostrada, el escalamiento seguirá este orden:

1. **Concurrencia controlada** — múltiples tasks en paralelo, mismo proceso
2. **Multiworker** — múltiples procesos, mismo servidor
3. **Queue externa** — Redis o similar para distribución de trabajo
4. **Workers remotos** — ejecución distribuida
5. **Orchestration** — scheduling, retry policies, dependencias entre tasks

Cada paso requiere que el anterior esté **validado operacionalmente**.

---

## 11. Regla CTO — No Negociable

> Si el runner no sobrevive errores, no mantiene consistencia,
> no recupera estado, no persiste correctamente —
> **entonces no se escala.**
>
> Primero estabilidad. Después velocidad. Después escala.

---

## 12. Consulta Obligatoria

Este archivo debe consultarse antes de:

- Crear un nuevo runner
- Crear un nuevo executor
- Agregar concurrencia
- Agregar orchestration
- Agregar escalamiento
- Modificar el flujo Task → Runner → Executor → PostgreSQL

**La arquitectura vive dentro del proyecto, no en memoria conversacional.**

---

*Última actualización: Subfase 3.5 — Runner Base*
*Proyecto: HERMES*
*Arquitecto: VULCAN + CTO*