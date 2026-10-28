# Guía de presentación

El presentador se elige al azar: **los tres** deben poder seguir este guion.

## 0. Antes de presentar (5 min)

```powershell
cd Proyecto1-Reservas-IA
.venv\Scripts\activate
python manage.py generar_historico     # deja los datos de demo limpios
python manage.py runserver
```

Ten abiertas dos ventanas: el navegador en http://127.0.0.1:8000/ y la **terminal del servidor** (ahí aparecen los correos de HU5).

## 1. Contexto (1 min)

- App base: gestor de reservas Django + SQLite + FullCalendar.
- Herramienta IA: Claude Code (CLI de escritorio).
- Antes de tocar código, la IA **analizó el proyecto** y encontró que no había flujo de pago, ni pruebas, y que el servidor no validaba bloqueos.

## 2. Demo (6–8 min)

| Paso | Qué hacer | Historia |
|------|-----------|----------|
| 1 | Entrar como `cliente2 / demo1234` → elegir **Pista Pádel 1** | |
| 2 | Mostrar el **mes coloreado** (verde/amarillo/rojo/gris) y la leyenda. Clic en un día gris → aviso. Clic en un día verde → abre las horas | **HU2** |
| 3 | Seleccionar una hora → pantalla de pago. Rellenar con `4242 4242 4242 4242`, `12/30`, `123`, **marcar "Guardar mis datos"** → confirmación | **HU1** |
| 4 | Mostrar en la terminal del servidor el **correo de confirmación** | **HU5** |
| 5 | Elegir otra hora → aparece **"Reservar con mis datos guardados (Visa •••• 4242)"** → un clic | **HU1** |
| 6 | Ir a **Mis reservas** → **Cancelar** una → correo de cancelación en la terminal → la hora vuelve a estar libre en el calendario | **HU4 + HU5** |
| 7 | Cerrar sesión, entrar como `admin / admin1234` → **Panel de demanda** | **HU3** |
| 8 | Explicar: histórico (azul) vs previsión (naranja punteada), demanda por día/hora, Pádel 1 = demanda **alta** → subir precio; Tenis = **baja** → descuentos. Usar el filtro por pista | **HU3** |

## 3. Proceso (3 min)

- **GitHub:** Issues #1–#5 (una historia cada uno) → ramas `feature/huN-…` → PRs #6–#12 con checklist de QA → CI en verde.
- **Pruebas:** `python manage.py test reservas` → 71 pruebas. Mostrar la pestaña *Actions* de GitHub.
- **AI Log** (`docs/AI_LOG.md`): mostrar 2–3 errores de la IA (prueba intermitente, día "lleno" por la noche, repo equivocado) y los cambios rechazados (merge automático).

## 4. Cambios que pueden pedir en vivo (dónde tocar)

| Petición probable | Archivo | Qué cambiar |
|-------------------|---------|-------------|
| Cambiar horario (p. ej. 8:00–22:00) | `reservas/services.py` | `HORA_APERTURA`, `HORA_CIERRE` |
| | `reservas/templates/reservas/calendario_full.html` | `slotMinTime`, `slotMaxTime` |
| Cambiar el precio de una pista | `/admin/` → Resources | campo *Price per hour* |
| Cambiar los umbrales de demanda alta/baja | `reservas/prevision.py` | `UMBRAL_ALTA`, `UMBRAL_BAJA` |
| Prever más o menos semanas | `reservas/prevision.py` | parámetro `horizonte` de `analizar_demanda` |
| Cambiar los colores del calendario | `calendario_full.html` | `coloresEstado` y la `.leyenda` |
| Limitar las semanas de repetición | `reservas/services.py` | `MAX_SEMANAS_REPETICION` |
| No permitir cancelar con menos de 24 h | `reservas/models.py` | propiedad `cancelable`: `self.start_time > timezone.now() + timedelta(hours=24)` (añadir `from datetime import timedelta`) |
| Cambiar el texto del correo | `reservas/notificaciones.py` | `enviar_confirmacion` / `enviar_cancelacion` |
| Bloquear un día (mantenimiento) | `/admin/` → Bloqueos | crear un bloqueo de 9:00 a 21:00 |

Después de cualquier cambio: `python manage.py test reservas` para demostrar que nada se rompió.

## 5. Preguntas probables

- **¿Se guarda la tarjeta?** Solo marca, últimos 4 dígitos y vencimiento; nunca el número completo ni el CVV. El pago es simulado.
- **¿Cómo se calcula la previsión?** Regresión lineal sobre las horas reservadas por semana de las últimas 12 semanas; ocupación = horas previstas / capacidad (12 h × 7 días por pista).
- **¿Qué hizo la IA y qué hicieron ustedes?** La IA propuso y generó código y pruebas; el equipo eligió el repositorio y las historias, autorizó la ejecución, revisó y fusionó los PRs, e hizo la QA manual. Los errores de la IA están en el AI Log.
