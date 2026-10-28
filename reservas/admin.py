from django.contrib import admin
from .models import Resource, Availability, Booking, PaymentProfile

# --- CONFIGURACIÓN DEL PANEL ADMIN ---

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'price_per_hour')  # Columnas que veremos en el admin
    search_fields = ('name',)                     # Buscar recursos por nombre


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ('id', 'resource', 'start_time', 'end_time')
    list_filter = ('resource',)                   # Filtro por recurso
    search_fields = ('resource__name',)
    verbose_name = 'Bloqueo'
    verbose_name_plural = 'Bloqueos'


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'resource', 'start_time', 'end_time', 'amount', 'payment_reference', 'created_at')
    list_filter = ('resource', 'user')
    search_fields = ('user__username', 'resource__name')


@admin.register(PaymentProfile)
class PaymentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'card_brand', 'card_last4', 'card_expiry', 'updated_at')
    search_fields = ('user__username', 'full_name')
