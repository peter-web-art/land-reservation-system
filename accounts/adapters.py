from django.urls import reverse
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .decorators import role_based_redirect


class RoleBasedAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        return reverse(role_based_redirect(request.user))


class RoleBasedSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_login_redirect_url(self, request, sociallogin):
        return reverse(role_based_redirect(sociallogin.user))
