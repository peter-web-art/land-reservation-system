from django.urls import path
from . import views
from . import payment_views

app_name = 'accounts'

urlpatterns = [
    path('login/',                            views.login_view,         name='login'),
    path('owner/login/',                      views.owner_login,        name='owner_login'),
    path('admin/login/',                      views.admin_login,        name='admin_login'),
    path('register/',                         views.register,          name='register'),
    path('register/verify/',                  views.register_verify,   name='register_verify'),
    path('profile/edit/',                     views.profile_edit,      name='profile_edit'),
    path('admin-portal/',                     views.admin_portal,      name='admin_portal'),
    path('admin-portal/register/',            views.admin_register_user, name='admin_register_user'),
    path('admin-portal/<int:user_id>/action/',views.admin_user_action, name='admin_user_action'),
    path('admin-portal/message/<int:user_id>/compose/', views.admin_compose_message, name='admin_compose_message'),
    path('admin-portal/message/<int:user_id>/thread/', views.admin_message_thread, name='admin_message_thread'),
    path('admin-portal/booking/<int:booking_id>/action/', views.admin_booking_action, name='admin_booking_action'),
    path('admin-portal/system/action/', views.admin_system_action, name='admin_system_action'),
    # Admin Payment Management
    path('admin-portal/payments/',            payment_views.admin_payments_dashboard, name='admin_payments_dashboard'),
    path('admin-portal/payments/<int:payment_id>/', payment_views.admin_payment_detail, name='admin_payment_detail'),
    path('admin-portal/payments/<int:payment_id>/confirm/', payment_views.admin_confirm_payment, name='admin_confirm_payment'),
    path('admin-portal/payments/<int:payment_id>/reject/', payment_views.admin_reject_payment, name='admin_reject_payment'),
    path('admin-portal/payments/analytics/', payment_views.admin_payment_analytics, name='admin_payment_analytics'),
    path('admin-portal/escrow/', payment_views.admin_escrow_tracker, name='admin_escrow_tracker'),
    path('admin-portal/escrow/<int:payment_id>/release/', payment_views.admin_release_payment, name='admin_release_payment'),
    path('admin-portal/escrow/<int:payment_id>/delay/', payment_views.admin_delay_payment, name='admin_delay_payment'),
    path('admin-portal/escrow/<int:payment_id>/refund/', payment_views.admin_refund_payment, name='admin_refund_payment'),
    # Admin message/inbox for owner requests
    path('admin-portal/owner-requests/', payment_views.admin_payment_requests, name='admin_payment_requests'),
    path('admin-portal/owner-requests/<int:message_id>/', payment_views.admin_message_detail, name='admin_message_detail'),
    # Owner Payment Details Management
    path('payment-details/', payment_views.owner_payment_details, name='owner_payment_details'),
    # Admin Operator Payment Configuration
    path('admin-portal/payment-config/', payment_views.admin_operator_payment_config, name='admin_operator_payment_config'),
    path('admin-portal/payment-config/add/', payment_views.admin_operator_payment_config_add, name='admin_operator_payment_config_add'),
    path('admin-portal/payment-config/<int:config_id>/edit/', payment_views.admin_operator_payment_config_edit, name='admin_operator_payment_config_edit'),
    path('admin-portal/payment-config/<int:config_id>/delete/', payment_views.admin_operator_payment_config_delete, name='admin_operator_payment_config_delete'),
    path('admin-portal/payment-config/<int:config_id>/toggle/', payment_views.admin_operator_payment_config_toggle, name='admin_operator_payment_config_toggle'),
    # Admin Owner Payment Details Management
    path('admin-portal/owner-payment-details/', payment_views.admin_owner_payment_details, name='admin_owner_payment_details'),
    path('admin-portal/owner-payment-details/<int:payment_detail_id>/review/', payment_views.admin_owner_payment_details_review, name='admin_owner_payment_details_review'),
    # Owner Payment Dashboard & Tracking
    path('owner/payments/', payment_views.owner_payment_dashboard, name='owner_payment_dashboard'),
    path('owner/payments/<int:payment_id>/', payment_views.owner_payment_detail, name='owner_payment_detail'),
    # Owner requests are handled by admin now; owner-request endpoint removed
    path('owner/communication/', payment_views.owner_communication_list, name='owner_communication_list'),
]
