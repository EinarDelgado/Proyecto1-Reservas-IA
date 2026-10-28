"""HU5 - Correo de confirmación al reservar y al cancelar."""
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase

from reservas.models import Booking, PaymentProfile, Resource
from reservas.notificaciones import enviar_confirmacion

from .utils import manana_a_las


class CorreosTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ana', password='x', email='ana@test.com', first_name='Ana')
        self.pista = Resource.objects.create(name='Pista Pádel 1')
        self.franja = {'start': manana_a_las(10).isoformat(), 'end': manana_a_las(11).isoformat()}
        PaymentProfile.objects.create(user=self.user, full_name='Ana', phone='1', card_brand='Visa',
                                      card_last4='4242', card_expiry='12/39')
        self.client.force_login(self.user)

    def test_correo_al_reservar(self):
        self.client.post(f'/reservar/{self.pista.id}/', {**self.franja, 'use_saved': '1', 'repeat_weeks': '1'})
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, ['ana@test.com'])
        self.assertIn('Reserva confirmada: Pista Pádel 1', correo.subject)
        referencia = Booking.objects.first().payment_reference
        self.assertIn(referencia, correo.body)
        self.assertEqual(correo.body.count('  - '), 2)  # reserva + repetición

    def test_correo_usa_el_email_del_formulario_de_pago(self):
        self.user.email = ''
        self.user.save()
        self.client.post(f'/reservar/{self.pista.id}/', {
            **self.franja, 'full_name': 'Ana', 'email': 'nuevo@test.com', 'phone': '1',
            'card_number': '4242424242424242', 'card_expiry': '12/39', 'cvv': '123'})
        self.assertEqual(mail.outbox[0].to, ['nuevo@test.com'])

    def test_correo_al_cancelar(self):
        reserva = Booking.objects.create(user=self.user, resource=self.pista,
                                         start_time=manana_a_las(10), end_time=manana_a_las(11))
        self.client.post(f'/mis-reservas/{reserva.id}/cancelar/')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Reserva cancelada', mail.outbox[0].subject)

    def test_reserva_fallida_no_envia_correo(self):
        otro = User.objects.create_user('beto', password='x')
        Booking.objects.create(user=otro, resource=self.pista,
                               start_time=manana_a_las(10), end_time=manana_a_las(11))
        self.client.post(f'/reservar/{self.pista.id}/', {**self.franja, 'use_saved': '1'})
        self.assertEqual(len(mail.outbox), 0)

    def test_sin_email_no_falla_ni_envia(self):
        sin_email = User.objects.create_user('carlos', password='x')
        reserva = Booking.objects.create(user=sin_email, resource=self.pista,
                                         start_time=manana_a_las(14), end_time=manana_a_las(15))
        self.assertFalse(enviar_confirmacion(sin_email, [reserva]))
        self.assertEqual(len(mail.outbox), 0)
