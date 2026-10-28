from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Página principal
    path('calendario/<int:resource_id>/', views.calendario, name='calendario'),
    path('calendario_full/<int:resource_id>/', views.calendario_full, name='calendario_full'),
    path('api/reservas/<int:resource_id>/', views.api_reservas, name='api_reservas'),
    path('api/reservas/crear/', views.api_crear_reserva, name='api_crear_reserva'),
    path('api/disponibilidad/<int:resource_id>/', views.api_disponibilidad, name='api_disponibilidad'),
    path('reservar/<int:resource_id>/', views.checkout, name='checkout'),
    path('reservas/confirmacion/<str:referencia>/', views.reserva_confirmada, name='reserva_confirmada'),
    path('mis-reservas/', views.mis_reservas, name='mis_reservas'),
    path('mis-reservas/<int:booking_id>/cancelar/', views.cancelar_reserva, name='cancelar_reserva'),
    path('mis-datos-pago/borrar/', views.borrar_datos_pago, name='borrar_datos_pago'),
    path('panel/demanda/', views.panel_demanda, name='panel_demanda'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),



]
