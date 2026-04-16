from django.core.validators import RegexValidator
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
    phone_validator = RegexValidator(
        regex=r'^\+?91?\d{10}$',
        message="Enter a valid phone number (e.g. 9876543210 or +919876543210)"
    )

    phone_number = models.CharField(
        max_length=15,
        unique=True,
        validators=[phone_validator]
    )
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

    def get_url(self):
        if self.CategoryName == "Template":
            return "template"
        elif self.CategoryName == "E-Books":
            return "ebooks"
        elif self.CategoryName == "PDFs":
            return "pdfs"
        elif self.CategoryName == "Source Code / Projects":
            return "sourcecode"
        elif self.CategoryName == "Courses & Tutorials":
            return "courses"
        elif self.CategoryName == "Tools & Resources":
            return "tools"
        return "#"

class Product(models.Model):
    CategoryId = models.ForeignKey(Category,on_delete=models.CASCADE)
    ProductName = models.CharField(max_length=255)
    ProductPrice = models.FloatField()
    ProductDiscountPrice = models.FloatField(blank=True, null=True)
    ShortDescription = models.TextField()
    LongDescription = RichTextField()
    ProductImage1 = models.ImageField(upload_to='products/productsimages/')
    ProductImage2 = models.ImageField(upload_to='products/productsimages/')
    ProductImage3 = models.ImageField(upload_to='products/productsimages/')
    ProductFile = models.FileField(upload_to='products/productsFile/', blank=True, null=True)
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
    ProgrammingLanguage = models.CharField(max_length=100, blank=True, null=True)
    Framework = models.CharField(max_length=100, blank=True, null=True)
    Database = models.CharField(max_length=100, blank=True, null=True)
    Platform = models.CharField(max_length=50, blank=True, null=True)
    SoftwareRequirements = models.TextField(blank=True, null=True)
    Features = models.TextField(blank=True, null=True)
    FilesIncluded = models.TextField(blank=True, null=True)
    DemoVideo = models.FileField(
        upload_to='products/demo_videos/',
        blank=True,
        null=True
    )

class ProductLesson(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="lessons"
    )
    title = models.CharField(max_length=255)
    video = models.FileField(upload_to="products/lessons/")
    is_preview = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)


class Certificate(models.Model):
    user = models.ForeignKey(ClientUser, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    certificate_file = models.FileField(upload_to="products/certificates/", blank=True, null=True)
    issued_date = models.DateTimeField(auto_now_add=True)

class LessonProgress(models.Model):
    user = models.ForeignKey(ClientUser, on_delete=models.CASCADE)
    lesson = models.ForeignKey(ProductLesson, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)


class Cart(models.Model):
    user = models.ForeignKey(ClientUser,on_delete=models.CASCADE)
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now_add=True)


class Order(models.Model):
    client = models.ForeignKey(ClientUser,on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    payment_id = models.CharField(max_length=255, blank=True, null=True,unique=True)
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

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200,blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    title = models.CharField(max_length=200)

    sender_name = models.CharField(max_length=100, blank=True, null=True)
    sender_email = models.EmailField(blank=True, null=True)

    subject = models.CharField(max_length=200, blank=True, null=True)
    message = models.TextField()

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
