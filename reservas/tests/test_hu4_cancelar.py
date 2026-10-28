"""HU4 - Ver y cancelar mis reservas."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from reservas.models import Booking, Resource
from reservas.services import crear_reservas, disponibilidad_por_dia

from .utils import manana_a_las


class CancelarReservaTests(TestCase):
    def setUp(self):
        self.ana = User.objects.create_user('ana', password='x')
        self.beto = User.objects.create_user('beto', password='x')
        self.pista = Resource.objects.create(name='Pista 1')
        self.reserva = Booking.objects.create(user=self.ana, resource=self.pista,
                                              start_time=manana_a_las(10), end_time=manana_a_las(11))
        self.client.force_login(self.ana)

    def cancelar(self, reserva):
        return self.client.post(f'/mis-reservas/{reserva.id}/cancelar/')

    def test_mis_reservas_lista_solo_las_mias(self):
        Booking.objects.create(user=self.beto, resource=self.pista,
                               start_time=manana_a_las(14), end_time=manana_a_las(15))
        r = self.client.get('/mis-reservas/')
        self.assertEqual(r.context['proximas'], [self.reserva])

    def test_mis_reservas_requiere_login(self):
        self.client.logout()
        self.assertEqual(self.client.get('/mis-reservas/').status_code, 302)

    def test_cancelar_reserva_futura(self):
        r = self.cancelar(self.reserva)
        self.assertRedirects(r, '/mis-reservas/')
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, Booking.CANCELADA)
        self.assertIsNotNone(self.reserva.cancelled_at)

    def test_no_puedo_cancelar_reserva_de_otro(self):
        ajena = Booking.objects.create(user=self.beto, resource=self.pista,
                                       start_time=manana_a_las(14), end_time=manana_a_las(15))
        self.assertEqual(self.cancelar(ajena).status_code, 404)
        ajena.refresh_from_db()
        self.assertEqual(ajena.status, Booking.CONFIRMADA)

    def test_no_puedo_cancelar_reserva_pasada(self):
        pasada = Booking.objects.create(user=self.ana, resource=self.pista,
                                        start_time=manana_a_las(10, dias=-2), end_time=manana_a_las(11, dias=-2))
        self.cancelar(pasada)
        pasada.refresh_from_db()
        self.assertEqual(pasada.status, Booking.CONFIRMADA)

    def test_cancelar_requiere_post(self):
        self.assertEqual(self.client.get(f'/mis-reservas/{self.reserva.id}/cancelar/').status_code, 405)

    def test_franja_cancelada_vuelve_a_estar_disponible(self):
        dia = timezone.localdate() + timedelta(days=1)
        self.assertEqual(disponibilidad_por_dia(self.pista, dia, dia)[0]['libres'], 11)
        self.cancelar(self.reserva)
        self.assertEqual(disponibilidad_por_dia(self.pista, dia, dia)[0]['libres'], 12)
        eventos = self.client.get(f'/api/reservas/{self.pista.id}/').json()
        self.assertEqual(eventos, [])

    def test_otra_persona_puede_reservar_la_franja_cancelada(self):
        # Antes unique_together(resource, start_time, end_time) lo impedía
        self.cancelar(self.reserva)
        nuevas = crear_reservas(self.beto, self.pista, manana_a_las(10), manana_a_las(11))
        self.assertEqual(len(nuevas), 1)
