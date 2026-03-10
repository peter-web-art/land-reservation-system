from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    is_owner = models.BooleanField(default=True)  # Only owners have accounts

# Create your models here.
