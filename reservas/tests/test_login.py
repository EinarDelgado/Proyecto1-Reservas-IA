from django.contrib.auth.models import User
from django.test import TestCase


class LoginTests(TestCase):
    def setUp(self):
        User.objects.create_user('ana', password='clave-segura-123')

    def test_login_correcto_redirige_a_inicio(self):
        r = self.client.post('/login/', {'username': 'ana', 'password': 'clave-segura-123'})
        self.assertRedirects(r, '/', fetch_redirect_response=False)

    def test_login_respeta_next_interno(self):
        r = self.client.post('/login/?next=/calendario_full/1/', {'username': 'ana', 'password': 'clave-segura-123'})
        self.assertRedirects(r, '/calendario_full/1/', fetch_redirect_response=False)

    def test_login_ignora_next_externo(self):
        r = self.client.post('/login/?next=https://sitio-malicioso.com/', {'username': 'ana', 'password': 'clave-segura-123'})
        self.assertRedirects(r, '/', fetch_redirect_response=False)

    def test_login_incorrecto_muestra_error(self):
        r = self.client.post('/login/', {'username': 'ana', 'password': 'mala'})
        self.assertContains(r, 'Usuario o contraseña incorrectos')
