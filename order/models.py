from django.db import models
from django.conf import settings
from shop.models import Books

# Create your models here.

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart',blank = True ,null= True)
    item = models.ForeignKey(Books, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1) 
    purchased = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.item} x {self.quantity}"

    def get_total_price(self):
        total_price = self.item.price * self.quantity
        return format(total_price, '0.2f')
    
    

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='order')
    orderitems = models.ManyToManyField(Cart)
    ordered = models.BooleanField(default = False)
    created = models.DateTimeField(auto_now_add = True)
    paymentID = models.CharField(max_length=255,blank = True,null=True)
    orderID = models.CharField(max_length=255,blank = True,null=True)

    def __str__(self):
        return f'Order For: {self.user.username}'
    
    def calculate_totals(self):
        total = 0
        for item in self.orderitems.all():
            total += float(item.get_total_price())
        return format(total, '0.2f')