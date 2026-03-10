from django.db import models
from django.db import models
from accounts.models import User

class Land(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=200)
    image = models.ImageField(upload_to='lands/', blank=True, null=True)

    def __str__(self):
        return self.title

# Create your models here.
