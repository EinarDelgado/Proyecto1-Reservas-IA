"""HU1 - Reservar directamente usando los datos de pago guardados."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from reservas.forms import PagoForm, luhn_valido, marca_tarjeta
from reservas.models import Booking, PaymentProfile, Resource

from .utils import manana_a_las

TARJETA_VISA = '4242 4242 4242 4242'


class FormularioPagoTests(TestCase):
    def datos(self, **cambios):
        datos = {'full_name': 'Ana Pérez', 'email': 'ana@test.com', 'phone': '6000-0000',
                 'card_number': TARJETA_VISA, 'card_expiry': '12/39', 'cvv': '123', 'repeat_weeks': 0}
        datos.update(cambios)
        return datos

    def test_luhn(self):
        self.assertTrue(luhn_valido('4242424242424242'))
        self.assertFalse(luhn_valido('4242424242424241'))

    def test_marca(self):
        self.assertEqual(marca_tarjeta('4242424242424242'), 'Visa')
        self.assertEqual(marca_tarjeta('5555555555554444'), 'Mastercard')
        self.assertEqual(marca_tarjeta('378282246310005'), 'Amex')

    def test_formulario_valido(self):
        form = PagoForm(self.datos())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['card_number'], '4242424242424242')

    def test_tarjeta_invalida(self):
        self.assertIn('card_number', PagoForm(self.datos(card_number='1234 5678 9012 3456')).errors)

    def test_tarjeta_vencida(self):
        self.assertIn('card_expiry', PagoForm(self.datos(card_expiry='01/20')).errors)

    def test_cvv_invalido(self):
        self.assertIn('cvv', PagoForm(self.datos(cvv='12a')).errors)


class CheckoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ana', password='x')
        self.pista = Resource.objects.create(name='Pista 1', price_per_hour=Decimal('12.50'))
        self.start = manana_a_las(10)
        self.end = manana_a_las(12)
        self.url = f'/reservar/{self.pista.id}/'
        self.franja = {'start': self.start.isoformat(), 'end': self.end.isoformat()}
        self.client.force_login(self.user)

    def pago(self, **cambios):
        datos = {**self.franja, 'full_name': 'Ana Pérez', 'email': 'ana@test.com', 'phone': '6000-0000',
                 'card_number': TARJETA_VISA, 'card_expiry': '12/39', 'cvv': '123', 'repeat_weeks': 0}
        datos.update(cambios)
        return datos

    def guardar_perfil(self):
        return PaymentProfile.objects.create(user=self.user, full_name='Ana Pérez', phone='6000-0000',
                                             card_brand='Visa', card_last4='4242', card_expiry='12/39')

    def test_requiere_login(self):
        self.client.logout()
        r = self.client.get(self.url, self.franja)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith('/login/?next=/reservar/'))

    def test_primera_vez_muestra_formulario_y_calcula_importe(self):
        r = self.client.get(self.url, self.franja)
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'Reservar con mis datos guardados')
        self.assertContains(r, 'Número de tarjeta')
        self.assertEqual(r.context['importe'], Decimal('25.00'))  # 2 h x 12.50

    def test_pagar_y_guardar_datos_solo_guarda_ultimos_4(self):
        r = self.client.post(self.url, self.pago(save_data='on'))
        reserva = Booking.objects.get()
        self.assertRedirects(r, f'/reservas/confirmacion/{reserva.payment_reference}/')
        self.assertEqual(reserva.amount, Decimal('25.00'))
        perfil = PaymentProfile.objects.get(user=self.user)
        self.assertEqual(perfil.card_last4, '4242')
        self.assertEqual(perfil.card_brand, 'Visa')
        # Nunca se guarda el número completo ni el CVV
        # (se excluye updated_at: sus microsegundos podrían contener "123" por casualidad)
        valores = ' '.join(str(v) for k, v in PaymentProfile.objects.values().get().items() if k != 'updated_at')
        self.assertNotIn('4242424242424242', valores)
        self.assertNotIn('123', valores)

    def test_pagar_sin_marcar_guardar_no_crea_perfil(self):
        self.client.post(self.url, self.pago())
        self.assertEqual(Booking.objects.count(), 1)
        self.assertFalse(PaymentProfile.objects.exists())

    def test_usuario_recurrente_ve_reserva_rapida(self):
        self.guardar_perfil()
        r = self.client.get(self.url, self.franja)
        self.assertContains(r, 'Reservar con mis datos guardados')
        self.assertContains(r, 'Visa •••• 4242')

    def test_usuario_recurrente_reserva_sin_rellenar_formulario(self):
        self.guardar_perfil()
        r = self.client.post(self.url, {**self.franja, 'use_saved': '1', 'repeat_weeks': '1'})
        self.assertEqual(r.status_code, 302)
        reservas = Booking.objects.filter(user=self.user)
        self.assertEqual(reservas.count(), 2)  # la reserva + 1 repetición
        self.assertEqual(len({b.payment_reference for b in reservas}), 1)

    def test_usar_guardados_sin_perfil_no_reserva(self):
        r = self.client.post(self.url, {**self.franja, 'use_saved': '1'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Booking.objects.exists())

    def test_formulario_con_errores_no_reserva(self):
        r = self.client.post(self.url, self.pago(card_number='1111'))
        self.assertContains(r, 'Número de tarjeta inválido')
        self.assertFalse(Booking.objects.exists())

    def test_franja_ocupada_muestra_error(self):
        otro = User.objects.create_user('beto', password='x')
        Booking.objects.create(user=otro, resource=self.pista, start_time=self.start, end_time=self.end)
        self.guardar_perfil()
        r = self.client.post(self.url, {**self.franja, 'use_saved': '1'})
        self.assertContains(r, 'Ya existe una reserva')
        self.assertEqual(Booking.objects.count(), 1)

    def test_franja_invalida_vuelve_al_calendario(self):
        r = self.client.get(self.url, {'start': 'basura'})
        self.assertRedirects(r, f'/calendario_full/{self.pista.id}/', fetch_redirect_response=False)

    def test_borrar_datos_guardados(self):
        self.guardar_perfil()
        r = self.client.post('/mis-datos-pago/borrar/', {'next': self.url})
        self.assertRedirects(r, self.url, fetch_redirect_response=False)
        self.assertFalse(PaymentProfile.objects.exists())

    def test_borrar_datos_requiere_post(self):
        self.guardar_perfil()
        self.assertEqual(self.client.get('/mis-datos-pago/borrar/').status_code, 405)
        self.assertTrue(PaymentProfile.objects.exists())

    def test_confirmacion_de_otro_usuario_da_404(self):
        self.client.post(self.url, self.pago())
        referencia = Booking.objects.get().payment_reference
        self.client.force_login(User.objects.create_user('beto', password='x'))
        self.assertEqual(self.client.get(f'/reservas/confirmacion/{referencia}/').status_code, 404)
