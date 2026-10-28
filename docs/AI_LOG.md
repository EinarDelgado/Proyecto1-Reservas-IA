# AI Development Log — Proyecto 1

**Grupo:** Einar Delgado · Estiven Quintero · Ahmed Alonso
**Herramienta IA principal:** Claude Code (CLI de escritorio, modelo Claude Opus 5.5)
**Aplicación base:** [JStack-Dev/Gestor-de-reservas](https://github.com/JStack-Dev/Gestor-de-reservas) (Django 5 + SQLite + FullCalendar)

Solo se registran las interacciones que afectaron significativamente el desarrollo.

## Registro

| # | Actividad | Herramienta IA | Qué se solicitó | Resultado | Decisión humana |
|---|-----------|----------------|-----------------|-----------|-----------------|
| 1 | Selección de repositorio | Claude Code | Leer el enunciado y recomendar el repo más sencillo | Recomendó Django (Gestor-de-reservas) por usar SQLite y traer FullCalendar | Aceptada |
| 2 | Análisis / Arquitectura | Claude Code | Analizar el proyecto existente antes de modificar código | Detectó: no existe flujo de pago (HU1 lo requiere), falta `requirements.txt`, `tests.py` vacío, la API no valida bloqueos del admin en servidor, `@csrf_exempt` en la API de reservas | Aceptada; se incorporó a los criterios de aceptación de HU1 y HU2 |
| 3 | Configuración Git | Claude Code | Crear labels e issues en el repo propio | **Error de la IA:** `gh` apuntó al repo original (JStack-Dev) en vez del nuestro; la operación falló con 404 | Corregido: se fijó `gh repo set-default` a nuestro repo y se verificó que no se creó nada en el repo ajeno |

## Respuestas incorrectas de la IA

1. **#3** — Ejecutó comandos de GitHub contra el repositorio equivocado (upstream) por no fijar el repo por defecto tras renombrar los remotos.

## Cambios de la IA rechazados

_(se completa durante el sprint)_

## Decisiones tomadas por humanos

- Elegir el repo Django por tiempo disponible (entrega al día siguiente).
- Repositorio privado con los 3 integrantes como colaboradores.
- Historias adicionales elegidas: HU4 (cancelar reservas) y HU5 (correo de confirmación).
- La IA no puede ejecutar el código clonado sin aprobación explícita del equipo (política de permisos de la herramienta).
