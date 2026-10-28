import re

from django import forms
from django.utils import timezone

from .services import MAX_SEMANAS_REPETICION


def luhn_valido(numero):
    """Algoritmo de Luhn: detecta números de tarjeta mal escritos."""
    total = 0
    for i, digito in enumerate(reversed(numero)):
        n = int(digito)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def marca_tarjeta(numero):
    if numero.startswith('4'):
        return 'Visa'
    if numero[:2] in {'51', '52', '53', '54', '55'} or '2221' <= numero[:4] <= '2720':
        return 'Mastercard'
    if numero[:2] in {'34', '37'}:
        return 'Amex'
    return 'Tarjeta'


class RepeticionForm(forms.Form):
    repeat_weeks = forms.IntegerField(
        label='Repetir semanalmente (semanas extra)', min_value=0,
        max_value=MAX_SEMANAS_REPETICION, initial=0, required=False,
    )

    def clean_repeat_weeks(self):
        return self.cleaned_data['repeat_weeks'] or 0


class PagoForm(RepeticionForm):
    """
    Formulario de pago (simulado: no hay pasarela real).
    El número completo y el CVV solo se validan; nunca se guardan.
    """
    full_name = forms.CharField(label='Nombre completo', max_length=120)
    email = forms.EmailField(label='Correo electrónico')
    phone = forms.CharField(label='Teléfono', max_length=20)
    card_number = forms.CharField(label='Número de tarjeta', max_length=23)
    card_expiry = forms.CharField(label='Vencimiento (MM/AA)', max_length=5)
    cvv = forms.CharField(label='CVV', max_length=4, widget=forms.PasswordInput(render_value=False))
    save_data = forms.BooleanField(label='Guardar mis datos para próximas reservas', required=False)

    def clean_card_number(self):
        numero = re.sub(r'[\s-]', '', self.cleaned_data['card_number'])
        if not numero.isdigit() or not 13 <= len(numero) <= 19 or not luhn_valido(numero):
            raise forms.ValidationError('Número de tarjeta inválido.')
        return numero

    def clean_card_expiry(self):
        valor = self.cleaned_data['card_expiry'].strip()
        m = re.fullmatch(r'(0[1-9]|1[0-2])/(\d{2})', valor)
        if not m:
            raise forms.ValidationError('Usa el formato MM/AA.')
        mes, anio = int(m.group(1)), 2000 + int(m.group(2))
        hoy = timezone.localdate()
        if (anio, mes) < (hoy.year, hoy.month):
            raise forms.ValidationError('La tarjeta está vencida.')
        return valor

    def clean_cvv(self):
        cvv = self.cleaned_data['cvv']
        if not re.fullmatch(r'\d{3,4}', cvv):
            raise forms.ValidationError('CVV inválido.')
        return cvv
