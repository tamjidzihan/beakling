from django.db import models
from django.conf import settings
from django.contrib import admin


class Customer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    full_name = models.CharField(max_length=200,blank=True,null=True)
    address = models.TextField(max_length=300,blank=True,null=True)
    country = models.CharField(max_length=100,blank=True,null=True)
    city = models.CharField(max_length=100,blank=True,null=True)
    zipcode = models.CharField(max_length=15,blank=True,null=True)
    phone = models.CharField(max_length=16,blank=True,null=True)
    date_of_birth = models.DateField(null=True)

    def email(self):
        return self.user.email

    def __str__(self):
        return f'{self.user.username}'

