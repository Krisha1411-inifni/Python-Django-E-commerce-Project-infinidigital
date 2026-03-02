from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from ckeditor.fields import RichTextField
from django.utils.text import slugify


# Create your models here.

class ClientUser(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    password = models.CharField(max_length=128)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

class Category(models.Model):
    CategoryName = models.CharField(max_length=255)
    CategoryDescription = models.TextField()
    CreationDate = models.DateTimeField(auto_now_add=True)
    UpdationDate = models.DateTimeField(auto_now_add=True)

class Product(models.Model):
    CategoryId = models.ForeignKey(Category,on_delete=models.CASCADE)
    ProductName = models.CharField(max_length=255)
    ProductPrice = models.FloatField()
    ProductDiscountPrice = models.FloatField()
    ShortDescription = models.TextField()
    LongDescription = RichTextField()
    ProductImage1 = models.ImageField(upload_to='products/productsimages/')
    ProductImage2 = models.ImageField(upload_to='products/productsimages/')
    ProductImage3 = models.ImageField(upload_to='products/productsimages/')
    ProductFile = models.FileField(upload_to='products/productsFile/')
    PreviewFile = models.FileField(
        upload_to='products/preview/',
        blank=True,
        null=True
    )
    CreationDate = models.DateTimeField(auto_now_add=True)
    UpdationDate = models.DateTimeField(auto_now=True)

    DemoFolder = models.CharField(max_length=255,
        blank=True,
        help_text="Auto-generated demo folder name"
    )

class Cart(models.Model):
    user = models.ForeignKey(ClientUser,on_delete=models.CASCADE)
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now_add=True)

class Order(models.Model):
    client = models.ForeignKey(ClientUser,on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    payment_id = models.CharField(max_length=255, blank=True, null=True)
    payment_provider = models.CharField(max_length=50,
        choices=[("stripe", "Stripe"), ("razorpay", "Razorpay"),("upi","UPI")],
        blank=True,
        null=True)
    is_verified = models.BooleanField(default=False)  # 🔐 KEY
    payment_submitted_at = models.DateTimeField(blank=True, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now_add=True)

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)