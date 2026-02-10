"""
URL configuration for infinidigital project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from tkinter.font import names

from django.contrib import admin
from django.urls import path
from products import views
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',views.index,name="home"),
    path('TopicDetail/<int:id>/',views.topic_detail,name="topic_detail"),
    path('TopicListing',views.topic_listing, name="topic_listing"),
    path('OurServices',views.our_services, name="services"),
    path('Template',views.template),
    path('EBooks',views.e_books),
    path('PDFs',views.pdfs),
    path('SourceCode',views.source_code),
    path('Courses',views.courses),
    path('Tools',views.tools),
    path('Contact',views.contact, name = "contact"),
    path('cart/', views.cart, name="cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("create-order/", views.create_order, name="create_order"),

    # 💳 Payment
    path("payment/<int:order_id>/", views.payment, name="payment"),
    path("payment-pending/<int:order_id>/", views.payment_pending, name="payment_pending"),

    # 📥 Downloads
    path("my-downloads/", views.my_downloads, name="my_downloads"),
    path("download/<int:product_id>/", views.download_product, name="download_product"),
    path("download-zip/", views.download_zip, name="download_zip"),
    path('client_Signup',views.client_signup, name = "client_signup"),
    path('client_Signout/', views.client_signout, name='client_signout'),
    path('client_activate/<uidb64>/<token>', views.client_activate, name='client_activate'),
    path(
        "template_demo/<path:path>",
        serve,
        {"document_root": settings.DEMO_ROOT},
    ),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)