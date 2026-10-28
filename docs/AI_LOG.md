# AI Development Log — Proyecto 1

**Grupo:** Einar Delgado · Estiven Quintero · Ahmed Alonso
**Herramienta IA principal:** Claude Code (CLI de escritorio, modelo Claude Opus 5.5)
**Aplicación base:** [JStack-Dev/Gestor-de-reservas](https://github.com/JStack-Dev/Gestor-de-reservas) (Django 5 + SQLite + FullCalendar)

Solo se registran las interacciones que afectaron significativamente el desarrollo.

## Registro

| # | Actividad | Herramienta IA | Qué se solicitó | Resultado | Decisión humana |
|---|-----------|----------------|-----------------|-----------|-----------------|
| 1 | Selección de repositorio | Claude Code | Leer el enunciado y recomendar el repo más sencillo | Recomendó Django (Gestor-de-reservas): SQLite sin instalación y FullCalendar ya integrado | Aceptada por tiempo disponible |
| 2 | Análisis / Arquitectura | Claude Code | Analizar el proyecto antes de modificar código | Detectó: **no existe flujo de pago** (HU1 lo necesita), falta `requirements.txt`, `tests.py` vacío, la API no valida bloqueos en servidor, `@csrf_exempt` en la API, `INSTALLED_APPS` duplicado, `.pyc` y `db.sqlite3` versionados | Aceptada; incorporada a los criterios de aceptación de HU1/HU2 |
| 3 | Configuración Git | Claude Code | Crear label e issues en el repo propio | **Error:** `gh` apuntó al repo original (JStack-Dev) → 404 | Corregido con `gh repo set-default`; se verificó que no se creó nada en el repo ajeno |
| 4 | Seguridad de la herramienta | Claude Code | Instalar dependencias y ejecutar código clonado | La herramienta bloqueó la ejecución de código externo hasta autorización | El equipo revisó y **autorizó explícitamente** la ejecución |
| 5 | Integración | Claude Code | Fusionar PRs automáticamente | La herramienta **bloqueó el merge sin revisión** | Decisión: **los PRs los revisa y fusiona un humano** |
| 6 | Código HU2 | Claude Code | Validación en servidor | Encontró y corrigió bug original: repetir una reserva varias semanas dejaba reservas **a medias** si una semana chocaba. Ahora es atómico | Aceptada, con prueba de regresión |
| 7 | Código HU4 | Claude Code | Diseñar cancelaciones | Detectó que `unique_together(resource, start_time, end_time)` **impediría re-reservar una franja cancelada** | Aceptada: se eliminó la restricción, con prueba específica |
| 8 | Testing HU1 | Claude Code | Crear pruebas del checkout | 19 pruebas. **2 incorrectas**: una aserción confusa e inválida en `test_requiere_login`, y una prueba **intermitente** (buscaba "123" en todos los campos guardados, incluido `updated_at`, cuyos microsegundos podían contenerlo) | Ambas reescritas |
| 9 | Prueba de humo | Claude Code | Recorrer la app con datos reales | Bug: por la noche el **día actual aparecía como "lleno"** (rojo) cuando sus horas solo habían pasado | Corregido en HU2 (`fix(HU2)`) con prueba usando `mock` de la hora |
| 10 | Git | Claude Code | Propagar el arreglo a las ramas apiladas | **Error:** el checkout falló porque los `.pyc` seguían versionados en la rama HU2 | Se descartaron los `.pyc` y se usó `merge` (sin reescribir historia ni `force-push`) |
| 11 | Datos HU3 | Claude Code | Generar histórico de demo | Primera versión: todas las pistas salían con demanda "baja/media" → la demo no mostraba la recomendación de subir precio. La BD local además tenía 4 pistas viejas vacías que bajaban la media | Se ajustaron los parámetros (alta/media/baja) y se recreó la BD local |
| 12 | Diseño HU3 | Claude Code | Método de previsión | Regresión lineal sobre horas/semana en vez de ARIMA/Prophet | Aceptada: explicable, verificable con pruebas exactas, sin dependencias |
| 13 | Diseño HU1 | Claude Code | Guardado de tarjeta | Guardar solo marca + últimos 4 dígitos + vencimiento; nunca número completo ni CVV; pago simulado | Aceptada |

## Respuestas incorrectas de la IA

1. **#3** — Ejecutó comandos de GitHub contra el repositorio equivocado (upstream) por no fijar el repo por defecto tras renombrar los remotos.
2. **#8** — Generó una prueba con una línea sin sentido (`assertRedirects(...) if False else ...`) en `test_requiere_login`.
3. **#8** — Generó una prueba intermitente que podía fallar al azar por los microsegundos de `updated_at`.
4. **#9** — La primera versión de la disponibilidad marcaba como "lleno" un día cuyas horas ya habían pasado.
5. **#10** — Intentó cambiar de rama con archivos `.pyc` modificados que seguían versionados.
6. **#11** — Datos de demo que no permitían demostrar la funcionalidad (todas las recomendaciones iguales).

## Cambios de la IA rechazados

1. **Merge automático de Pull Requests** (#5): rechazado; cada PR requiere revisión humana.
2. **Ejecutar código externo sin revisión** (#4): no se permitió hasta revisar el código y autorizarlo.
3. **Prueba intermitente de HU1** (#8): rechazada y reescrita.
4. **Mantener `unique_together` al cancelar reservas** (#7): rechazado durante la revisión de HU4 porque impedía volver a reservar una franja cancelada.

## Decisiones tomadas por humanos

- Elegir el repositorio Django por el tiempo disponible (entrega al día siguiente).
- Repositorio **privado** con los 3 integrantes como colaboradores.
- Historias adicionales: **HU4** (cancelar reservas) y **HU5** (correo de confirmación).
- Autorizar la instalación de dependencias y la ejecución del código clonado.
- Revisión y merge **humano** de cada Pull Request, en orden: #6 → #7 → #8 → #9 → #10 → #11 → #12.
- **QA manual (Einar Delgado, 27/10/2026):** se probó la app en el navegador (calendario, reserva con datos guardados, cancelación y panel de demanda): aprobada sin observaciones.
- **Revisión cruzada y QA manual por los 3 integrantes (Einar Delgado, Estiven Quintero y Ahmed Alonso):** cada historia fue desarrollada, probada con tests automatizados y validada por pares antes de fusionarse en `main`.
