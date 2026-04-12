from django.urls import path
from . import views

app_name = "lands"

urlpatterns = [
    path('',                                            views.land_list,                 name='land_list'),
    path('search/',                                     views.search_lands,              name='search_lands'),
    path('api/location-autocomplete/',                  views.location_autocomplete,     name='location_autocomplete'),
    path('<int:pk>/',                                   views.land_detail,               name='land_detail'),
    path('<int:pk>/book/',                              views.book_land,                 name='book_land'),
    # Customer
    path('dashboard/customer/',                         views.customer_dashboard,        name='customer_dashboard'),
    path('reservations/',                               views.my_reservations,           name='my_reservations'),
    path('reservations/<int:pk>/cancel/',               views.cancel_reservation,        name='cancel_reservation'),
    # Owner
    path('dashboard/',                                  views.owner_dashboard,           name='owner_dashboard'),
    path('add/',                                        views.add_land,                  name='add_land'),
    path('<int:pk>/edit/',                              views.edit_land,                 name='edit_land'),
    path('<int:pk>/delete/',                            views.delete_land,               name='delete_land'),
    path('reservations/manage/',                        views.reservations_management,   name='reservations_management'),
    path('reservations/calendar/',                      views.calendar_view,             name='calendar_view'),
    path('reservations/<int:pk>/status/<str:status>/',  views.update_reservation_status, name='update_reservation_status'),
    path('reservations/<int:pk>/payment/',              views.mark_payment,              name='mark_payment'),
    path('<int:pk>/report/',  views.report_listing, name='report_listing'),
    # Messaging
    path('messages/',                                   views.inbox,            name='inbox'),
    path('messages/send/',                              views.send_message,     name='send_message'),
    path('messages/<int:user_id>/',                     views.message_thread,   name='message_thread'),
    # Wishlist
    path('<int:pk>/wishlist/',                          views.toggle_wishlist,  name='toggle_wishlist'),
    path('wishlist/',                                   views.my_wishlist,      name='my_wishlist'),
    # Switch modes
    path('switch-to-owner/',                            views.switch_to_owner,  name='switch_to_owner'),
    path('switch-mode/',                                views.switch_mode,      name='switch_mode'),
    # Help Center
    path('help/',                                       views.help_center,      name='help_center'),
    # Notifications
    path('notifications/',                              views.my_notifications, name='my_notifications'),
    path('notifications/<int:notification_id>/read/',   views.mark_notification_read, name='mark_notification_read'),
]
