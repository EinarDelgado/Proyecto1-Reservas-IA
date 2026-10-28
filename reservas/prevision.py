"""
HU3: previsión de la demanda a partir del histórico de reservas.

Se usa una regresión lineal simple sobre las horas reservadas por semana: es
fácil de explicar y de verificar, y no necesita librerías externas.
"""
from collections import Counter
from datetime import timedelta

from django.utils import timezone

from .models import Booking
from .services import HORA_APERTURA, HORA_CIERRE

DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
CAPACIDAD_SEMANAL_HORAS = 7 * (HORA_CIERRE - HORA_APERTURA)  # por pista
UMBRAL_ALTA = 75   # % de ocupación prevista
UMBRAL_BAJA = 30


def lunes_de(fecha):
    return fecha - timedelta(days=fecha.weekday())


def regresion_lineal(valores):
    """Mínimos cuadrados sobre x = 0..n-1. Devuelve (pendiente, intercepto)."""
    n = len(valores)
    if n == 0:
        return 0.0, 0.0
    if n == 1:
        return 0.0, float(valores[0])
    media_x = (n - 1) / 2
    media_y = sum(valores) / n
    sxx = sum((x - media_x) ** 2 for x in range(n))
    sxy = sum((x - media_x) * (y - media_y) for x, y in enumerate(valores))
    pendiente = sxy / sxx
    return pendiente, media_y - pendiente * media_x


def pronosticar(valores, horizonte=4):
    """Prolonga la recta de tendencia `horizonte` periodos (nunca por debajo de 0)."""
    pendiente, intercepto = regresion_lineal(valores)
    n = len(valores)
    return [max(0.0, round(intercepto + pendiente * (n + i), 1)) for i in range(horizonte)]


def recomendar(ocupacion_prevista, pendiente):
    tendencia = 'al alza' if pendiente > 0.5 else 'a la baja' if pendiente < -0.5 else 'estable'
    if ocupacion_prevista >= UMBRAL_ALTA:
        nivel = 'alta'
        accion = 'Subir el precio un 10–15 % en horas pico o ampliar horario/inventario.'
    elif ocupacion_prevista <= UMBRAL_BAJA:
        nivel = 'baja'
        accion = 'Aplicar descuentos del 10–20 % o promociones en horas valle.'
    else:
        nivel = 'media'
        accion = 'Mantener el precio y vigilar las horas pico.'
    return {'nivel': nivel, 'tendencia': tendencia, 'accion': accion}


def analizar_demanda(recursos, semanas_historico=12, horizonte=4, hoy=None):
    """
    Agrega las reservas confirmadas de las últimas `semanas_historico` semanas
    completas de los `recursos` indicados y prevé las `horizonte` siguientes.
    """
    hoy = hoy or timezone.localdate()
    lunes_actual = lunes_de(hoy)
    inicio = lunes_actual - timedelta(weeks=semanas_historico)

    horas_semana = [0.0] * semanas_historico
    horas_dia = Counter()
    horas_hora = Counter()
    reservas = Booking.objects.activas().filter(
        resource__in=recursos, start_time__date__gte=inicio, start_time__date__lt=lunes_actual,
    ).values_list('start_time', 'end_time')
    for start, end in reservas:
        local = timezone.localtime(start)
        horas = (end - start).total_seconds() / 3600
        horas_semana[(lunes_de(local.date()) - inicio).days // 7] += horas
        horas_dia[local.weekday()] += horas
        horas_hora[local.hour] += horas

    prevision = pronosticar(horas_semana, horizonte)
    pendiente, _ = regresion_lineal(horas_semana)
    capacidad = CAPACIDAD_SEMANAL_HORAS * len(recursos)
    ocupacion_prevista = round(100 * sum(prevision) / (horizonte * capacidad), 1) if capacidad else 0.0
    ultimas = horas_semana[-4:]
    ocupacion_actual = round(100 * sum(ultimas) / (len(ultimas) * capacidad), 1) if capacidad and ultimas else 0.0

    return {
        'etiquetas_historico': [(inicio + timedelta(weeks=i)).strftime('%d/%m') for i in range(semanas_historico)],
        'etiquetas_prevision': [(lunes_actual + timedelta(weeks=i)).strftime('%d/%m') for i in range(horizonte)],
        'historico': [round(h, 1) for h in horas_semana],
        'prevision': prevision,
        'por_dia': [round(horas_dia[d], 1) for d in range(7)],
        'por_hora': [round(horas_hora[h], 1) for h in range(HORA_APERTURA, HORA_CIERRE)],
        'etiquetas_horas': [f'{h}:00' for h in range(HORA_APERTURA, HORA_CIERRE)],
        'horas_pico': [f'{h}:00' for h, _ in horas_hora.most_common(3)],
        'pendiente': round(pendiente, 2),
        'ocupacion_actual': ocupacion_actual,
        'ocupacion_prevista': ocupacion_prevista,
        'recomendacion': recomendar(ocupacion_prevista, pendiente),
    }
