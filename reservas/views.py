import json
import uuid
from decimal import Decimal
from datetime import date, datetime, timedelta, time
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.dateformat import format as date_format
from django.utils.dateparse import parse_datetime
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import PagoForm, RepeticionForm, marca_tarjeta
from .models import Resource, Booking, Availability, PaymentProfile
from .services import ReservaError, crear_reservas, disponibilidad_por_dia


# Horario por defecto (si no hay Availability definida)
DEFAULT_START = time(9, 0)   # 09:00
DEFAULT_END = time(21, 0)    # 21:00


def calendario(request, resource_id):
    """
    Muestra un calendario semanal de reservas para un recurso.
    """
    resource = get_object_or_404(Resource, id=resource_id)

    hoy = datetime.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())  # Lunes
    dias_semana = [inicio_semana + timedelta(days=i) for i in range(7)]

    reservas = Booking.objects.activas().filter(
        resource=resource,
        start_time__date__gte=inicio_semana,
        start_time__date__lte=inicio_semana + timedelta(days=6)
    ).order_by('start_time')

    reservas_por_dia = {date_format(dia, 'Y-m-d'): [] for dia in dias_semana}
    for reserva in reservas:
        clave = date_format(reserva.start_time, 'Y-m-d')
        reservas_por_dia[clave].append(reserva)

    return render(request, 'reservas/calendario.html', {
        'resource': resource,
        'dias_semana': dias_semana,
        'reservas_por_dia': reservas_por_dia,
    })


def calendario_navegable(request, resource_id):
    """
    Calendario semanal con botones de semana anterior/siguiente.
    """
    resource = get_object_or_404(Resource, id=resource_id)

    hoy = datetime.today()
    delta = 0
    if request.GET.get('week') == 'prev':
        delta = -7
    elif request.GET.get('week') == 'next':
        delta = 7

    inicio_semana = (hoy - timedelta(days=hoy.weekday())) + timedelta(days=delta)
    dias_semana = [inicio_semana + timedelta(days=i) for i in range(7)]

    reservas = Booking.objects.activas().filter(
        resource=resource,
        start_time__date__gte=inicio_semana,
        start_time__date__lte=inicio_semana + timedelta(days=6)
    ).order_by('start_time')

    reservas_por_dia = {date_format(dia, 'Y-m-d'): [] for dia in dias_semana}
    for reserva in reservas:
        clave = date_format(reserva.start_time, 'Y-m-d')
        reservas_por_dia[clave].append(reserva)

    return render(request, 'reservas/calendario.html', {
        'resource': resource,
        'dias_semana': dias_semana,
        'reservas_por_dia': reservas_por_dia,
    })


@ensure_csrf_cookie  # el JS del calendario envía el token CSRF en sus peticiones POST
def calendario_full(request, resource_id):
    """
    Calendario interactivo con FullCalendar.
    """
    resource = get_object_or_404(Resource, id=resource_id)

    reservas = Booking.objects.activas().filter(resource=resource).order_by('start_time')
    bloqueos = Availability.objects.filter(resource=resource)

    # Lista de reservas
    reservas_json = [
        {
            "start": reserva.start_time.isoformat(),
            "end": reserva.end_time.isoformat(),
            "title": f"Reservado por {reserva.user.username}",
            "color": "#10b981",  # Verde reservas
        }
        for reserva in reservas
    ]

    # Lista de bloqueos (rojo)
    bloqueos_json = [
        {
            "start": bloqueo.start_time.isoformat(),
            "end": bloqueo.end_time.isoformat(),
        }
        for bloqueo in bloqueos
    ]

    return render(request, 'reservas/calendario_full.html', {
        'resource': resource,
        'reservas_json': json.dumps(reservas_json),
        'bloqueos_json': json.dumps(bloqueos_json),
        'is_authenticated': request.user.is_authenticated,
    })



def api_crear_reserva(request):
    """
    Endpoint para crear una nueva reserva, con soporte para repeticiones semanales.
    La validación (bloqueos, solapamientos, horario) se hace en services.crear_reservas.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Debes iniciar sesión para reservar.'}, status=403)
    try:
        data = json.loads(request.body)
        resource = get_object_or_404(Resource, id=data.get('resource_id'))
        start_time = parse_datetime(data.get('start_time') or '')
        end_time = parse_datetime(data.get('end_time') or '')
        if not start_time or not end_time:
            return JsonResponse({'success': False, 'error': 'Fechas inválidas.'}, status=400)
        repeat_weeks = int(data.get('repeat_weeks', 0))
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Datos inválidos.'}, status=400)

    try:
        reservas = crear_reservas(request.user, resource, start_time, end_time, repeat_weeks)
    except ReservaError as exc:
        return JsonResponse({'success': False, 'error': str(exc)})

    return JsonResponse({'success': True, 'reservas': [
        {'start': r.start_time.isoformat(), 'end': r.end_time.isoformat()} for r in reservas
    ]})


def api_disponibilidad(request, resource_id):
    """
    Disponibilidad por día para el calendario mensual.
    Parámetros: start (incluido) y end (excluido) en formato YYYY-MM-DD, como los envía FullCalendar.
    """
    resource = get_object_or_404(Resource, id=resource_id)
    try:
        desde = date.fromisoformat(request.GET['start'][:10])
        hasta = date.fromisoformat(request.GET['end'][:10]) - timedelta(days=1)
    except (KeyError, ValueError):
        return JsonResponse({'error': 'Parámetros start y end requeridos (YYYY-MM-DD).'}, status=400)
    if hasta < desde or (hasta - desde).days > 62:
        return JsonResponse({'error': 'Rango de fechas inválido (máximo 62 días).'}, status=400)
    return JsonResponse(disponibilidad_por_dia(resource, desde, hasta), safe=False)


def login_view(request):
    """
    Vista para el inicio de sesión de usuarios.
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            # Volver a la página que pidió el login (p. ej. el checkout), solo si es de nuestro sitio
            next_url = request.GET.get('next', '')
            if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('/')
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
    return render(request, 'reservas/login.html')


def logout_view(request):
    """
    Cerrar sesión.
    """
    logout(request)
    return redirect('/login/')

def api_reservas(request, resource_id):
    """
    API que devuelve todas las reservas de un recurso en formato JSON.
    """
    reservas = Booking.objects.activas().filter(resource_id=resource_id).order_by('start_time')
    # No exponemos el nombre de otros usuarios: solo se distingue "Mi reserva"
    eventos = [
        {
            "title": "Mi reserva" if reserva.user_id == request.user.id else "Ocupado",
            "start": reserva.start_time.isoformat(),
            "end": reserva.end_time.isoformat(),
            "color": "#2563eb" if reserva.user_id == request.user.id else "#6b7280",
        }
        for reserva in reservas
    ]
    return JsonResponse(eventos, safe=False)

def home(request):
    """
    Vista principal que muestra todas las pistas (resources).
    """
    resources = Resource.objects.all()  # Obtenemos todas las pistas
    return render(request, 'reservas/home.html', {'resources': resources})



def _franja_desde(datos):
    """Lee start/end (ISO 8601) de GET o POST; si vienen sin zona horaria se asume la local."""
    franja = []
    for clave in ('start', 'end'):
        valor = parse_datetime(datos.get(clave) or '')
        if valor and timezone.is_naive(valor):
            valor = timezone.make_aware(valor)
        franja.append(valor)
    return franja


@login_required
def checkout(request, resource_id):
    """
    HU1: confirmar y pagar una reserva. Si el usuario tiene datos guardados puede
    reservar con un solo clic sin volver a rellenar el formulario de pago.
    """
    resource = get_object_or_404(Resource, id=resource_id)
    datos = request.POST if request.method == 'POST' else request.GET
    start, end = _franja_desde(datos)
    if not start or not end or start >= end:
        messages.error(request, 'Franja horaria inválida. Selecciónala de nuevo en el calendario.')
        return redirect('calendario_full', resource_id=resource.id)

    perfil = PaymentProfile.objects.filter(user=request.user).first()
    horas = Decimal((end - start).total_seconds()) / Decimal(3600)
    importe = (resource.price_per_hour * horas).quantize(Decimal('0.01'))

    usar_guardados = request.method == 'POST' and 'use_saved' in request.POST and perfil is not None
    form_pago = PagoForm(
        request.POST if request.method == 'POST' and not usar_guardados else None,
        initial={'full_name': perfil.full_name if perfil else request.user.get_full_name(),
                 'phone': perfil.phone if perfil else '',
                 'email': request.user.email},
    )
    form_rapido = RepeticionForm(request.POST if usar_guardados else None)

    if request.method == 'POST':
        form = form_rapido if usar_guardados else form_pago
        if form.is_valid():
            referencia = 'PAY-' + uuid.uuid4().hex[:10].upper()
            try:
                crear_reservas(request.user, resource, start, end, form.cleaned_data['repeat_weeks'],
                               amount=importe, payment_reference=referencia)
            except ReservaError as exc:
                messages.error(request, str(exc))
            else:
                if not usar_guardados:
                    pago = form_pago.cleaned_data
                    request.user.email = pago['email']
                    request.user.save(update_fields=['email'])
                    if pago['save_data']:
                        PaymentProfile.objects.update_or_create(user=request.user, defaults={
                            'full_name': pago['full_name'],
                            'phone': pago['phone'],
                            'card_brand': marca_tarjeta(pago['card_number']),
                            'card_last4': pago['card_number'][-4:],
                            'card_expiry': pago['card_expiry'],
                        })
                return redirect('reserva_confirmada', referencia=referencia)

    return render(request, 'reservas/checkout.html', {
        'resource': resource,
        'start': start,
        'end': end,
        'importe': importe,
        'perfil': perfil,
        'form_pago': form_pago,
        'form_rapido': form_rapido,
        'mostrar_formulario': perfil is None or (request.method == 'POST' and not usar_guardados),
    })


@login_required
def reserva_confirmada(request, referencia):
    reservas = Booking.objects.filter(user=request.user, payment_reference=referencia).select_related('resource')
    if not reservas:
        raise Http404('Reserva no encontrada')
    return render(request, 'reservas/confirmacion.html', {
        'reservas': reservas,
        'referencia': referencia,
        'total': sum(r.amount for r in reservas),
    })


@login_required
@require_POST
def borrar_datos_pago(request):
    PaymentProfile.objects.filter(user=request.user).delete()
    messages.success(request, 'Tus datos de pago guardados se han eliminado.')
    next_url = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('home')


@login_required
def mis_reservas(request):
    """HU4: listado de reservas del usuario, con opción de cancelar las futuras."""
    reservas = Booking.objects.filter(user=request.user).select_related('resource').order_by('-start_time')
    ahora = timezone.now()
    return render(request, 'reservas/mis_reservas.html', {
        'proximas': [r for r in reservas if r.start_time > ahora and r.status == Booking.CONFIRMADA],
        'historial': [r for r in reservas if r.start_time <= ahora or r.status == Booking.CANCELADA],
        'perfil': PaymentProfile.objects.filter(user=request.user).first(),
    })


@login_required
@require_POST
def cancelar_reserva(request, booking_id):
    # Filtrar por usuario: una reserva ajena responde 404, como si no existiera
    reserva = get_object_or_404(Booking, id=booking_id, user=request.user)
    if not reserva.cancelable:
        messages.error(request, 'Esta reserva ya no se puede cancelar.')
        return redirect('mis_reservas')

    reserva.status = Booking.CANCELADA
    reserva.cancelled_at = timezone.now()
    reserva.save(update_fields=['status', 'cancelled_at'])
    messages.success(request, f'Reserva cancelada. Se reembolsarán ${reserva.amount} (reembolso simulado).')
    return redirect('mis_reservas')
