from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/',                            views.login_view,         name='login'),
    path('owner/login/',                      views.owner_login,        name='owner_login'),
    path('admin/login/',                      views.admin_login,        name='admin_login'),
    path('register/',                         views.register,          name='register'),
    path('profile/edit/',                     views.profile_edit,      name='profile_edit'),
    path('admin-portal/',                     views.admin_portal,      name='admin_portal'),
    path('admin-portal/register/',            views.admin_register_user, name='admin_register_user'),
    path('admin-portal/<int:user_id>/action/',views.admin_user_action, name='admin_user_action'),
    path('admin-portal/booking/<int:booking_id>/action/', views.admin_booking_action, name='admin_booking_action'),
    path('admin-portal/system/action/', views.admin_system_action, name='admin_system_action'),
]
