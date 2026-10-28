from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone


class Resource(models.Model):
    """Recurso que puede reservarse (pistas, salas, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    price_per_hour = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('10.00'))

    def __str__(self):
        return self.name


class Availability(models.Model):
    """Horarios disponibles para cada recurso."""
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='availabilities')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    def __str__(self):
        return f"{self.resource.name} - {self.start_time} a {self.end_time}"
    
    class Meta:
        verbose_name = 'Bloqueo'
        verbose_name_plural = 'Bloqueos'


class BookingQuerySet(models.QuerySet):
    def activas(self):
        """Reservas que ocupan la pista (las canceladas no cuentan)."""
        return self.filter(status=Booking.CONFIRMADA)


class Booking(models.Model):
    """Reserva de un recurso por un usuario."""
    CONFIRMADA = 'confirmada'
    CANCELADA = 'cancelada'
    ESTADOS = [(CONFIRMADA, 'Confirmada'), (CANCELADA, 'Cancelada')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='bookings')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    # Las reservas repetidas de un mismo pago comparten referencia
    payment_reference = models.CharField(max_length=20, blank=True, db_index=True)
    status = models.CharField(max_length=12, choices=ESTADOS, default=CONFIRMADA)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    objects = BookingQuerySet.as_manager()

    def __str__(self):
        return f"Reserva de {self.resource.name} por {self.user.username}"

    def clean(self):
        """
        Validación para evitar que haya reservas solapadas con la misma franja horaria.
        """
        overlapping = Booking.objects.activas().filter(
            resource=self.resource,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        ).exclude(pk=self.pk)  # Excluimos la propia reserva al editar

        if overlapping.exists():
            raise ValidationError("Ya existe una reserva en esta franja horaria.")

    @property
    def cancelable(self):
        return self.status == self.CONFIRMADA and self.start_time > timezone.now()

    # Nota: se eliminó unique_together(resource, start_time, end_time) porque impedía
    # volver a reservar una franja cancelada. Los solapamientos se validan en services.py.


class PaymentProfile(models.Model):
    """
    Datos de pago guardados por un usuario recurrente (HU1).
    Por seguridad nunca se guarda el número completo de la tarjeta ni el CVV.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='payment_profile')
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    card_brand = models.CharField(max_length=20)
    card_last4 = models.CharField(max_length=4)
    card_expiry = models.CharField(max_length=5)  # MM/AA
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Datos de pago guardados'
        verbose_name_plural = 'Datos de pago guardados'

    def __str__(self):
        return f"{self.card_brand} •••• {self.card_last4} ({self.user.username})"
