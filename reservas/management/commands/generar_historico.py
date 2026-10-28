"""
Genera datos de demostración: pistas con precio, un administrador, clientes y
varias semanas de reservas con patrones realistas (fines de semana y tardes
más demandados, tendencia creciente) para la previsión de demanda (HU3).
"""
import random
from datetime import datetime, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from reservas.models import Booking, PaymentProfile, Resource

PISTAS = [
    # nombre, descripción, precio/hora, demanda base
    ('Pista Pádel 1', 'Pista de pádel exterior', 12, 1.5),
    ('Pista Pádel 2', 'Pista de pádel cubierta', 15, 0.8),
    ('Pista Tenis', 'Pista de tierra batida', 10, 0.3),
    ('Cancha Fútbol 5', 'Césped artificial con iluminación', 40, 0.6),
]
FACTOR_DIA = [0.6, 0.65, 0.7, 0.8, 1.0, 1.2, 1.1]  # lunes..domingo
FACTOR_HORA = {9: 0.4, 10: 0.5, 11: 0.6, 12: 0.6, 13: 0.5, 14: 0.45,
               15: 0.5, 16: 0.7, 17: 0.9, 18: 1.0, 19: 1.0, 20: 0.8}


class Command(BaseCommand):
    help = "Crea pistas, usuarios de demo y un histórico de reservas (borra las reservas existentes de esas pistas)"

    def add_arguments(self, parser):
        parser.add_argument('--semanas', type=int, default=16, help='Semanas de histórico (por defecto 16)')
        parser.add_argument('--semilla', type=int, default=42, help='Semilla aleatoria para resultados repetibles')

    @transaction.atomic
    def handle(self, *args, semanas, semilla, **options):
        rnd = random.Random(semilla)

        recursos = []
        for nombre, descripcion, precio, base in PISTAS:
            recurso, _ = Resource.objects.update_or_create(
                name=nombre, defaults={'description': descripcion, 'price_per_hour': precio})
            recursos.append((recurso, base))

        admin, _ = User.objects.get_or_create(username='admin', defaults={'email': 'admin@demo.com'})
        admin.is_staff = admin.is_superuser = True
        admin.set_password('admin1234')
        admin.save()

        clientes = []
        for i, nombre in enumerate(['Carlos', 'María', 'Luis', 'Ana', 'Pedro', 'Sofía'], start=1):
            user, _ = User.objects.get_or_create(username=f'cliente{i}')
            user.first_name = nombre
            user.email = f'cliente{i}@demo.com'
            user.set_password('demo1234')
            user.save()
            clientes.append(user)

        # cliente1 es "usuario recurrente" con datos de pago guardados (HU1)
        PaymentProfile.objects.update_or_create(user=clientes[0], defaults={
            'full_name': 'Carlos Demo', 'phone': '6000-0001',
            'card_brand': 'Visa', 'card_last4': '4242', 'card_expiry': '12/30'})

        Booking.objects.filter(resource__in=[r for r, _ in recursos]).delete()

        ahora = timezone.now()
        hoy = timezone.localdate()
        inicio = hoy - timedelta(days=hoy.weekday()) - timedelta(weeks=semanas)
        fin = hoy + timedelta(days=14)
        nuevas = []
        dia = inicio
        while dia < fin:
            tendencia = 0.75 + 0.5 * min(1.0, (dia - inicio).days / (7 * semanas))
            for recurso, base in recursos:
                for hora in range(9, 21):
                    start = timezone.make_aware(datetime.combine(dia, time(hora)))
                    futura = start > ahora
                    probabilidad = base * FACTOR_DIA[dia.weekday()] * FACTOR_HORA[hora] * tendencia
                    if futura:
                        probabilidad *= 0.5  # el futuro aún se está llenando
                    if rnd.random() >= probabilidad:
                        continue
                    cancelada = not futura and rnd.random() < 0.06
                    nuevas.append(Booking(
                        user=rnd.choice(clientes), resource=recurso,
                        start_time=start, end_time=start + timedelta(hours=1),
                        amount=recurso.price_per_hour, payment_reference=f'DEMO-{len(nuevas):06d}',
                        status=Booking.CANCELADA if cancelada else Booking.CONFIRMADA,
                        cancelled_at=start - timedelta(days=1) if cancelada else None,
                    ))
            dia += timedelta(days=1)
        Booking.objects.bulk_create(nuevas)

        self.stdout.write(self.style.SUCCESS(
            f'{len(recursos)} pistas, {len(clientes)} clientes y {len(nuevas)} reservas generadas.\n'
            '  Administrador: admin / admin1234  (panel de demanda en /panel/demanda/)\n'
            '  Cliente con datos guardados: cliente1 / demo1234\n'
            '  Otros clientes: cliente2..cliente6 / demo1234'))
