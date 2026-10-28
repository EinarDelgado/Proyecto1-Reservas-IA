"""HU2 - Calendario dinámico con días disponibles y ocupados."""
import json
from datetime import datetime, time, timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from reservas.models import Availability, Booking, Resource
from reservas.services import ReservaError, crear_reservas, disponibilidad_por_dia

from .utils import manana_a_las


class DisponibilidadPorDiaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ana', password='x')
        self.pista = Resource.objects.create(name='Pista 1')
        self.manana = timezone.localdate() + timedelta(days=1)

    def estado(self, dia):
        return disponibilidad_por_dia(self.pista, dia, dia)[0]

    def test_dia_sin_reservas_es_libre(self):
        d = self.estado(self.manana)
        self.assertEqual(d['estado'], 'libre')
        self.assertEqual(d['libres'], 12)
        self.assertEqual(d['total'], 12)

    def test_dia_con_alguna_reserva_es_parcial(self):
        Booking.objects.create(user=self.user, resource=self.pista,
                               start_time=manana_a_las(10), end_time=manana_a_las(12))
        d = self.estado(self.manana)
        self.assertEqual(d['estado'], 'parcial')
        self.assertEqual(d['libres'], 10)

    def test_dia_bloqueado_completo_es_lleno(self):
        Availability.objects.create(resource=self.pista,
                                    start_time=manana_a_las(9), end_time=manana_a_las(21))
        self.assertEqual(self.estado(self.manana)['estado'], 'lleno')

    def test_dia_anterior_a_hoy_es_pasado(self):
        ayer = timezone.localdate() - timedelta(days=1)
        self.assertEqual(self.estado(ayer)['estado'], 'pasado')

    def test_dia_cuyas_horas_ya_pasaron_es_pasado_y_no_lleno(self):
        # Bug encontrado en la prueba de humo: hoy a las 22:00 aparecía en rojo como "lleno"
        hoy = timezone.localdate()
        noche = timezone.make_aware(datetime.combine(hoy, time(22)))
        with mock.patch('reservas.services.timezone.now', return_value=noche):
            self.assertEqual(disponibilidad_por_dia(self.pista, hoy, hoy)[0]['estado'], 'pasado')

    def test_reservas_de_otra_pista_no_afectan(self):
        otra = Resource.objects.create(name='Pista 2')
        Booking.objects.create(user=self.user, resource=otra,
                               start_time=manana_a_las(10), end_time=manana_a_las(11))
        self.assertEqual(self.estado(self.manana)['estado'], 'libre')


class ApiDisponibilidadTests(TestCase):
    def setUp(self):
        self.pista = Resource.objects.create(name='Pista 1')

    def test_devuelve_un_elemento_por_dia_con_end_excluido(self):
        hoy = timezone.localdate()
        fin = hoy + timedelta(days=7)
        r = self.client.get(f'/api/disponibilidad/{self.pista.id}/?start={hoy}&end={fin}')
        self.assertEqual(r.status_code, 200)
        dias = r.json()
        self.assertEqual(len(dias), 7)
        self.assertEqual(dias[0]['fecha'], hoy.isoformat())

    def test_acepta_fechas_con_hora_como_fullcalendar(self):
        r = self.client.get(f'/api/disponibilidad/{self.pista.id}/'
                            '?start=2030-01-01T00:00:00-05:00&end=2030-01-03T00:00:00-05:00')
        self.assertEqual(len(r.json()), 2)

    def test_parametros_invalidos_devuelven_400(self):
        self.assertEqual(self.client.get(f'/api/disponibilidad/{self.pista.id}/').status_code, 400)
        self.assertEqual(self.client.get(
            f'/api/disponibilidad/{self.pista.id}/?start=2030-01-01&end=2031-01-01').status_code, 400)

    def test_recurso_inexistente_devuelve_404(self):
        self.assertEqual(self.client.get('/api/disponibilidad/999/?start=2030-01-01&end=2030-01-02').status_code, 404)


class ValidacionEnServidorTests(TestCase):
    """Antes la API solo dependía del JavaScript para respetar bloqueos."""

    def setUp(self):
        self.user = User.objects.create_user('ana', password='x')
        self.pista = Resource.objects.create(name='Pista 1')

    def test_no_permite_reservar_en_franja_bloqueada(self):
        Availability.objects.create(resource=self.pista,
                                    start_time=manana_a_las(9), end_time=manana_a_las(13))
        with self.assertRaisesMessage(ReservaError, 'bloqueada'):
            crear_reservas(self.user, self.pista, manana_a_las(10), manana_a_las(11))

    def test_no_permite_reservar_en_el_pasado(self):
        ayer = manana_a_las(10, dias=-1)
        with self.assertRaisesMessage(ReservaError, 'pasada'):
            crear_reservas(self.user, self.pista, ayer, ayer + timedelta(hours=1))

    def test_no_permite_fuera_de_horario(self):
        with self.assertRaisesMessage(ReservaError, 'horario'):
            crear_reservas(self.user, self.pista, manana_a_las(7), manana_a_las(8))

    def test_conflicto_en_repeticion_no_deja_reservas_a_medias(self):
        # Ocupamos la tercera semana; antes se guardaban las dos primeras igualmente
        Booking.objects.create(user=self.user, resource=self.pista,
                               start_time=manana_a_las(10, dias=15), end_time=manana_a_las(11, dias=15))
        with self.assertRaisesMessage(ReservaError, 'Semana 3'):
            crear_reservas(self.user, self.pista, manana_a_las(10), manana_a_las(11), repeat_weeks=3)
        self.assertEqual(Booking.objects.count(), 1)

    def test_api_crear_reserva_respeta_bloqueos(self):
        Availability.objects.create(resource=self.pista,
                                    start_time=manana_a_las(9), end_time=manana_a_las(21))
        self.client.force_login(self.user)
        r = self.client.post('/api/reservas/crear/', json.dumps({
            'resource_id': self.pista.id,
            'start_time': manana_a_las(10).isoformat(),
            'end_time': manana_a_las(11).isoformat(),
        }), content_type='application/json')
        self.assertFalse(r.json()['success'])
        self.assertEqual(Booking.objects.count(), 0)

    def test_api_crear_reserva_correcta(self):
        self.client.force_login(self.user)
        r = self.client.post('/api/reservas/crear/', json.dumps({
            'resource_id': self.pista.id,
            'start_time': manana_a_las(10).isoformat(),
            'end_time': manana_a_las(11).isoformat(),
            'repeat_weeks': 1,
        }), content_type='application/json')
        self.assertTrue(r.json()['success'])
        self.assertEqual(Booking.objects.count(), 2)

    def test_api_eventos_no_expone_nombres_de_otros_usuarios(self):
        Booking.objects.create(user=self.user, resource=self.pista,
                               start_time=manana_a_las(10), end_time=manana_a_las(11))
        eventos = self.client.get(f'/api/reservas/{self.pista.id}/').json()
        self.assertEqual(eventos[0]['title'], 'Ocupado')
        self.client.force_login(self.user)
        eventos = self.client.get(f'/api/reservas/{self.pista.id}/').json()
        self.assertEqual(eventos[0]['title'], 'Mi reserva')

    def test_calendario_carga_y_entrega_cookie_csrf(self):
        r = self.client.get(f'/calendario_full/{self.pista.id}/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('csrftoken', r.cookies)
        self.assertContains(r, 'dayGridMonth')
