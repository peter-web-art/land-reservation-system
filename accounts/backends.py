from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class SuspendedAwareBackend(ModelBackend):
    """Blocks login for suspended users."""
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(request, username=username, password=password, **kwargs)
        if user and user.is_suspended:
            return None   # Refuse login silently — axes will show the lockout page
        return user
