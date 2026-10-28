"""
Lógica de negocio de reservas: validación de franjas y disponibilidad por día.
Se usa tanto desde las vistas HTML como desde la API.
"""
from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from .models import Availability, Booking

HORA_APERTURA = 9   # 09:00
HORA_CIERRE = 21    # 21:00
MAX_SEMANAS_REPETICION = 12


class ReservaError(Exception):
    """Error de negocio al intentar reservar (mensaje apto para mostrar al usuario)."""


def franja_ocupada(resource, start, end):
    return Booking.objects.filter(
        resource=resource, start_time__lt=end, end_time__gt=start
    ).exists()


def franja_bloqueada(resource, start, end):
    return Availability.objects.filter(
        resource=resource, start_time__lt=end, end_time__gt=start
    ).exists()


def validar_franja(resource, start, end):
    """Lanza ReservaError si la franja no se puede reservar."""
    if start >= end:
        raise ReservaError("La hora de fin debe ser posterior a la de inicio.")
    if start < timezone.now():
        raise ReservaError("No se puede reservar en una fecha u hora pasada.")

    inicio_local = timezone.localtime(start)
    fin_local = timezone.localtime(end)
    if (inicio_local.date() != fin_local.date()
            or inicio_local.time() < time(HORA_APERTURA)
            or fin_local.time() > time(HORA_CIERRE)):
        raise ReservaError(f"El horario de reservas es de {HORA_APERTURA}:00 a {HORA_CIERRE}:00.")

    if franja_bloqueada(resource, start, end):
        raise ReservaError("Esta franja horaria está bloqueada por el administrador.")
    if franja_ocupada(resource, start, end):
        raise ReservaError("Ya existe una reserva en esta franja horaria.")


@transaction.atomic
def crear_reservas(user, resource, start, end, repeat_weeks=0, **extra):
    """
    Crea la reserva y sus repeticiones semanales. Si alguna semana falla no se
    guarda ninguna (antes quedaban reservas a medias).
    `extra` permite guardar campos adicionales de Booking (importe, referencia de pago...).
    """
    if not 0 <= repeat_weeks <= MAX_SEMANAS_REPETICION:
        raise ReservaError(f"Puedes repetir la reserva entre 0 y {MAX_SEMANAS_REPETICION} semanas.")

    reservas = []
    for semana in range(repeat_weeks + 1):
        inicio = start + timedelta(weeks=semana)
        fin = end + timedelta(weeks=semana)
        try:
            validar_franja(resource, inicio, fin)
        except ReservaError as exc:
            if repeat_weeks:
                raise ReservaError(f"Semana {semana + 1} ({timezone.localtime(inicio):%d/%m/%Y}): {exc}")
            raise
        reservas.append(Booking.objects.create(
            user=user, resource=resource, start_time=inicio, end_time=fin, **extra
        ))
    return reservas


def disponibilidad_por_dia(resource, desde, hasta):
    """
    Devuelve, para cada día entre `desde` y `hasta` (ambos incluidos), cuántas
    franjas de 1 hora quedan libres y un estado: libre, parcial, lleno o pasado.
    """
    tz = timezone.get_current_timezone()
    inicio_rango = timezone.make_aware(datetime.combine(desde, time.min), tz)
    fin_rango = timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min), tz)

    # Una sola consulta por tabla para todo el rango
    ocupaciones = [
        (b.start_time, b.end_time)
        for b in Booking.objects.filter(resource=resource, start_time__lt=fin_rango, end_time__gt=inicio_rango)
    ] + [
        (b.start_time, b.end_time)
        for b in Availability.objects.filter(resource=resource, start_time__lt=fin_rango, end_time__gt=inicio_rango)
    ]

    ahora = timezone.now()
    hoy = timezone.localdate()
    total = HORA_CIERRE - HORA_APERTURA
    dias = []
    dia = desde
    while dia <= hasta:
        libres = 0
        for hora in range(HORA_APERTURA, HORA_CIERRE):
            inicio = timezone.make_aware(datetime.combine(dia, time(hora)), tz)
            fin = inicio + timedelta(hours=1)
            if inicio < ahora:
                continue
            if any(o_inicio < fin and o_fin > inicio for o_inicio, o_fin in ocupaciones):
                continue
            libres += 1

        if dia < hoy:
            estado = 'pasado'
        elif libres == 0:
            estado = 'lleno'
        elif libres == total:
            estado = 'libre'
        else:
            estado = 'parcial'
        dias.append({'fecha': dia.isoformat(), 'estado': estado, 'libres': libres, 'total': total})
        dia += timedelta(days=1)
    return dias
