from django.urls import path
from . import views

app_name = "lands"

urlpatterns = [
    path('dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('add/', views.add_land, name='add_land'),
    path('<int:pk>/edit/', views.edit_land, name='edit_land'),
    path('<int:pk>/delete/', views.delete_land, name='delete_land'),
    path('', views.land_list, name='land_list'),
    path('search/', views.search_lands, name='search_lands'),
    path('<int:pk>/', views.land_detail, name='land_detail'),
    path('<int:pk>/book/', views.book_land, name='book_land'),
    path('reservations/', views.my_reservations, name='my_reservations'),
    path('reservations/<int:pk>/cancel/', views.cancel_reservation, name='cancel_reservation'),
    path('dashboard/customer/', views.customer_dashboard, name='customer_dashboard'),
    path('reservations/manage/', views.reservations_management, name='reservations_management'),
    path('check-status/', views.check_booking_status, name='check_booking_status'),
    path('reservations/<int:pk>/status/<str:status>/', views.update_reservation_status, name='update_reservation_status'),
]
