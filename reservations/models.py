from django.db import models
from django.db import models
from lands.models import Land

class Reservation(models.Model):
    land = models.ForeignKey(Land, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    reserved_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer_name} - {self.land.title}"

# Create your models here.
