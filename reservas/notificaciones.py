"""HU5: correos de confirmación y cancelación de reservas."""
from django.core.mail import send_mail
from django.utils import timezone


def _franja(reserva):
    inicio = timezone.localtime(reserva.start_time)
    fin = timezone.localtime(reserva.end_time)
    return f"{inicio:%d/%m/%Y} de {inicio:%H:%M} a {fin:%H:%M}"


def _enviar(user, asunto, cuerpo):
    if not user.email:
        return False
    # fail_silently: un fallo del servidor de correo no debe anular una reserva ya pagada
    return send_mail(asunto, cuerpo, None, [user.email], fail_silently=True) == 1


def enviar_confirmacion(user, reservas):
    if not reservas:
        return False
    recurso = reservas[0].resource
    lineas = "\n".join(f"  - {_franja(r)}  (${r.amount})" for r in reservas)
    total = sum(r.amount for r in reservas)
    referencia = reservas[0].payment_reference or "—"
    cuerpo = (
        f"Hola {user.get_full_name() or user.username},\n\n"
        f"Tu reserva de {recurso.name} está confirmada:\n\n{lineas}\n\n"
        f"Total: ${total}\nReferencia de pago: {referencia}\n\n"
        "Puedes ver o cancelar tus reservas en 'Mis reservas'.\n\n"
        "Gestor de Reservas"
    )
    return _enviar(user, f"Reserva confirmada: {recurso.name}", cuerpo)


def enviar_cancelacion(reserva):
    cuerpo = (
        f"Hola {reserva.user.get_full_name() or reserva.user.username},\n\n"
        f"Tu reserva de {reserva.resource.name} del {_franja(reserva)} ha sido cancelada.\n"
        f"Reembolso: ${reserva.amount}\n\n"
        "Gestor de Reservas"
    )
    return _enviar(reserva.user, f"Reserva cancelada: {reserva.resource.name}", cuerpo)
