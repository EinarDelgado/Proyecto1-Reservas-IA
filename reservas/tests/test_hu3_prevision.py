"""HU3 - Gráficos de previsión de la demanda para el administrador."""
from datetime import datetime, time, timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from reservas.models import Booking, PaymentProfile, Resource
from reservas.prevision import analizar_demanda, lunes_de, pronosticar, recomendar, regresion_lineal


class CalculosTests(TestCase):
    def test_regresion_de_una_recta_exacta(self):
        pendiente, intercepto = regresion_lineal([2, 4, 6, 8])
        self.assertAlmostEqual(pendiente, 2)
        self.assertAlmostEqual(intercepto, 2)

    def test_pronostico_continua_la_tendencia(self):
        self.assertEqual(pronosticar([10, 20, 30], horizonte=2), [40.0, 50.0])

    def test_pronostico_nunca_es_negativo(self):
        self.assertEqual(pronosticar([30, 20, 10], horizonte=3), [0.0, 0.0, 0.0])

    def test_casos_borde(self):
        self.assertEqual(pronosticar([], horizonte=2), [0.0, 0.0])
        self.assertEqual(pronosticar([7], horizonte=2), [7.0, 7.0])

    def test_recomendaciones_por_umbral(self):
        self.assertEqual(recomendar(80, 0)['nivel'], 'alta')
        self.assertEqual(recomendar(50, 0)['nivel'], 'media')
        self.assertEqual(recomendar(10, 0)['nivel'], 'baja')
        self.assertEqual(recomendar(50, 3)['tendencia'], 'al alza')
        self.assertEqual(recomendar(50, -3)['tendencia'], 'a la baja')


class AnalizarDemandaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ana', password='x')
        self.pista = Resource.objects.create(name='Pista 1')
        self.lunes_actual = lunes_de(timezone.localdate())

    def reservar(self, semanas_atras, dia_semana=0, hora=18, horas=1, **extra):
        dia = self.lunes_actual - timedelta(weeks=semanas_atras) + timedelta(days=dia_semana)
        start = timezone.make_aware(datetime.combine(dia, time(hora)))
        return Booking.objects.create(user=self.user, resource=self.pista, start_time=start,
                                      end_time=start + timedelta(hours=horas), **extra)

    def test_agrupa_horas_por_semana(self):
        self.reservar(1, horas=2)   # semana pasada
        self.reservar(12)           # primera semana del histórico
        a = analizar_demanda([self.pista])
        self.assertEqual(len(a['historico']), 12)
        self.assertEqual(a['historico'][-1], 2.0)
        self.assertEqual(a['historico'][0], 1.0)

    def test_ignora_semana_actual_y_anteriores_al_rango(self):
        self.reservar(0)   # semana en curso (incompleta)
        self.reservar(13)  # fuera del histórico
        self.assertEqual(sum(analizar_demanda([self.pista])['historico']), 0)

    def test_ignora_canceladas(self):
        self.reservar(1, status=Booking.CANCELADA)
        self.assertEqual(sum(analizar_demanda([self.pista])['historico']), 0)

    def test_demanda_por_dia_y_hora(self):
        self.reservar(1, dia_semana=5, hora=19)  # sábado 19:00
        a = analizar_demanda([self.pista])
        self.assertEqual(a['por_dia'][5], 1.0)
        self.assertEqual(a['por_hora'][19 - 9], 1.0)
        self.assertEqual(a['horas_pico'], ['19:00'])

    def test_ocupacion_sobre_capacidad(self):
        # 84 h/semana de capacidad: 42 h en cada una de las últimas 4 semanas = 50 %
        for semana in range(1, 5):
            for dia in range(7):
                self.reservar(semana, dia_semana=dia, hora=9, horas=6)
        self.assertEqual(analizar_demanda([self.pista])['ocupacion_actual'], 50.0)


class PanelDemandaTests(TestCase):
    def setUp(self):
        self.pista = Resource.objects.create(name='Pista 1')
        self.admin = User.objects.create_user('jefe', password='x', is_staff=True)
        self.cliente = User.objects.create_user('ana', password='x')

    def test_cliente_no_puede_entrar(self):
        self.client.force_login(self.cliente)
        r = self.client.get('/panel/demanda/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/admin/login/', r.url)

    def test_anonimo_no_puede_entrar(self):
        self.assertEqual(self.client.get('/panel/demanda/').status_code, 302)

    def test_admin_ve_graficos(self):
        self.client.force_login(self.admin)
        r = self.client.get('/panel/demanda/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'grafico-semanal')
        self.assertContains(r, 'datos-demanda')
        self.assertEqual(len(r.context['por_recurso']), 1)

    def test_filtro_por_pista(self):
        otra = Resource.objects.create(name='Pista 2')
        self.client.force_login(self.admin)
        r = self.client.get(f'/panel/demanda/?recurso={otra.id}')
        self.assertEqual(r.context['seleccionado'], otra)

    def test_filtro_invalido_muestra_todas(self):
        self.client.force_login(self.admin)
        r = self.client.get('/panel/demanda/?recurso=abc')
        self.assertIsNone(r.context['seleccionado'])


class GenerarHistoricoTests(TestCase):
    def test_comando_crea_datos_de_demo(self):
        call_command('generar_historico', semanas=4, stdout=StringIO())
        self.assertEqual(Resource.objects.count(), 4)
        self.assertTrue(User.objects.get(username='admin').is_staff)
        self.assertTrue(PaymentProfile.objects.filter(user__username='cliente1').exists())
        self.assertGreater(Booking.objects.count(), 50)

    def test_comando_es_repetible(self):
        call_command('generar_historico', semanas=4, stdout=StringIO())
        primera = Booking.objects.count()
        call_command('generar_historico', semanas=4, stdout=StringIO())
        self.assertEqual(Booking.objects.count(), primera)
