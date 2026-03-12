from django.db import models
from accounts.models import User

class Land(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=200)
    LISTING_CHOICES = [
        ('rent', 'Rent'),
        ('sale', 'Sale'),
    ]
    listing_type = models.CharField(max_length=10, choices=LISTING_CHOICES, default='rent')
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    image = models.ImageField(upload_to='lands/', blank=True, null=True)

    def __str__(self):
        return self.title

class Reservation(models.Model):
    RESERVATION_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    land = models.ForeignKey(Land, on_delete=models.CASCADE, related_name='reservations')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations', null=True, blank=True)
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=RESERVATION_STATUS, default='pending')

    def __str__(self):
        return f"{self.customer.username} - {self.land.title}"
