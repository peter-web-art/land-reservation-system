from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/',                         views.register,          name='register'),
    path('profile/edit/',                     views.profile_edit,      name='profile_edit'),
    path('admin-portal/',                     views.admin_portal,      name='admin_portal'),
    path('admin-portal/<int:user_id>/action/',views.admin_user_action, name='admin_user_action'),
    path('kyc/submit/',                       views.submit_kyc,        name='submit_kyc'),
    path('kyc/<int:user_id>/review/',         views.review_kyc,        name='review_kyc'),
]
