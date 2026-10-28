# 🏟️ Gestor de Reservas — Proyecto 1 (Tópicos Especiales II)

**Desarrollo asistido por IA con herramientas de escritorio** · Prof. Regis Rivera

Sistema web de reservas de pistas (pádel, tenis, fútbol) en **Django 5 + SQLite + FullCalendar**, extendido en un *Feature Sprint* con 5 historias de usuario usando **Claude Code** (CLI de escritorio) como asistente de IA.

> Aplicación base: [JStack-Dev/Gestor-de-reservas](https://github.com/JStack-Dev/Gestor-de-reservas)

## 👥 Equipo y roles (rotativos)

| Historia | Developer | Reviewer | QA |
|----------|-----------|----------|----|
| HU1 – Datos de pago guardados | Einar Delgado | Estiven Quintero | Ahmed Alonso |
| HU2 – Calendario de disponibilidad | Estiven Quintero | Ahmed Alonso | Einar Delgado |
| HU3 – Previsión de demanda | Ahmed Alonso | Einar Delgado | Estiven Quintero |
| HU4 – Cancelar reservas | Einar Delgado | Ahmed Alonso | Estiven Quintero |
| HU5 – Correo de confirmación | Estiven Quintero | Einar Delgado | Ahmed Alonso |

## 📋 Historias de usuario

| # | Historia | Issue | PR |
|---|----------|-------|----|
| HU1 | Como **usuario recurrente**, quiero reservar directamente usando mis datos guardados, para no tener que rellenar el formulario de pago en cada compra. | #1 | #8 |
| HU2 | Como **cliente**, quiero ver un calendario dinámico con los días disponibles y ocupados, para elegir mi fecha rápidamente sin intentos fallidos. | #2 | #7 |
| HU3 | Como **administrador**, quiero ver gráficos de previsión de la demanda basados en el histórico, para ajustar los precios y el inventario de forma inteligente. | #3 | #11 |
| HU4 ➕ | Como **cliente**, quiero ver y cancelar mis reservas, para liberar el horario si no puedo asistir. | #4 | #9 |
| HU5 ➕ | Como **cliente**, quiero recibir un correo de confirmación al reservar o cancelar, para tener constancia de mi reserva. | #5 | #10 |

➕ = historias adicionales elegidas por el equipo.

## 🚀 Instalación (Windows)

```powershell
git clone https://github.com/EinarDelgado/Proyecto1-Reservas-IA.git
cd Proyecto1-Reservas-IA
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py generar_historico   # pistas, usuarios y 16 semanas de reservas de demo
python manage.py runserver
```

Abrir http://127.0.0.1:8000/

### Usuarios de demo

| Usuario | Contraseña | Para probar |
|---------|------------|-------------|
| `admin` | `admin1234` | Panel de demanda (`/panel/demanda/`) y `/admin/` |
| `cliente1` | `demo1234` | Usuario recurrente **con tarjeta guardada** (HU1) |
| `cliente2` … `cliente6` | `demo1234` | Usuarios sin datos guardados |

Tarjeta de prueba: `4242 4242 4242 4242`, vencimiento `12/30`, CVV `123` (el pago es **simulado**).

## ✅ Pruebas automatizadas

```powershell
python manage.py test reservas
```

71 pruebas en `reservas/tests/` (una por archivo y por historia). También corren automáticamente con **GitHub Actions** en cada push y Pull Request (`.github/workflows/tests.yml`).

## 🗂️ Estructura relevante

```
reservas/
├── services.py        # Validación de reservas y disponibilidad por día (HU2)
├── forms.py           # Formulario de pago: Luhn, vencimiento, CVV (HU1)
├── notificaciones.py  # Correos de confirmación/cancelación (HU5)
├── prevision.py       # Regresión lineal y recomendaciones (HU3)
├── views.py           # Vistas y API
├── management/commands/generar_historico.py   # Datos de demo
└── tests/             # test_hu1_… test_hu5_…, test_login
docs/
├── AI_LOG.md          # AI Development Log (evidencia de uso de IA)
└── PRESENTACION.md    # Guion de demo y dónde tocar ante cambios en vivo
```

## 🔀 Flujo de trabajo Git

- Una **rama por historia** (`feature/huN-…`) + `chore/…` y `docs/…`.
- Commits con prefijo convencional (`feat(HU1):`, `test(HU2):`, `fix(HU2):`) y referencia al issue (`Refs #N`).
- Cada historia se integra mediante un **Pull Request** con descripción, checklist de QA y revisión humana antes del merge.

## 🤖 Uso de IA

Ver [`docs/AI_LOG.md`](docs/AI_LOG.md): actividades, respuestas incorrectas de la IA, cambios rechazados y decisiones humanas.
