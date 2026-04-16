from django.contrib import admin

from .models import Product, Category, ClientUser, Order, OrderItem, Cart, ProductLesson, Certificate

# Register your models here.


admin.site.register(Product)
admin.site.register(ProductLesson)
admin.site.register(Certificate)
admin.site.register(Category)
admin.site.register(ClientUser)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Cart)