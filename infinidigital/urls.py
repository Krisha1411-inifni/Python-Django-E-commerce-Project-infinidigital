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
from django.urls import path, include
from products import views
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.conf import settings

from products.views import admin_products, admin_users

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',views.index,name="home"),
    path('TopicDetail/<int:id>/',views.topic_detail,name="topic_detail"),
    path(
    "certificate/<int:product_id>/",
    views.download_certificate,
    name="download_certificate"),
    path("course/<int:product_id>/", views.course_player, name="course_player"),
    path("complete-lesson/<int:lesson_id>/", views.complete_lesson, name="complete_lesson"),
    path('TopicListing',views.topic_listing, name="topic_listing"),
    path('services/',views.our_services, name="services"),
    path('template',views.template,name='template'),
    path('ebooks',views.e_books, name='ebooks'),
    path('pdfs',views.pdfs, name='pdfs'),
    path('sourcecode',views.source_code, name='sourcecode'),
    path('courses',views.courses, name='courses'),
    path('search/', views.search, name='search'),
    path('category/<int:id>/', views.category_page, name='category_page'),
    path('contact/',views.contact_view, name = "contact"),
    path("cart/", views.cart, name="cart"),
    path("add-to-cart/<int:product_id>/", views.add_to_cart, name="add_to_cart"),    path('remove-from-cart/<int:cart_id>/', views.remove_from_cart, name='remove_from_cart'),
    path("checkout/", views.checkout, name="checkout"),
    path("create-order/", views.create_order, name="create_order"),

    path("payment/<int:order_id>/", views.payment, name="payment"),
    path("payment-pending/<int:order_id>/", views.payment_pending, name="payment_pending"),

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

path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
path('products/', admin_products, name='admin_products'),
path('users/', admin_users, name='admin_users'),
path("add-product/", views.add_product, name="add_product"),
path('delete-product/', views.delete_product, name='delete_product'),
path('delete-user/', views.delete_user, name='delete_user'),
path("admin_login/", views.admin_login, name="admin_login"),
path("admin-register/", views.admin_register, name="admin_register"),
path("logout/", views.admin_logout, name="admin_logout"),
path(
    "admin-activate/<uidb64>/<token>/",
    views.admin_activate,
    name="admin_activate"
),
# Forgot password (enter email)
    path("forgot-password/", views.forgot_password, name="forgot_password"),

    # Reset password (via email link)
    path(
        "reset-password/<uidb64>/<token>/",
        views.reset_password,
        name="reset_password"
    ),
    path("admin_orders",views.admin_orders,name="admin_orders"),
    path('verify_order/',views.verify_order,name="verify_order"),
    path('admin_category/',views.admin_category,name="admin_category"),
    path('add_category/',views.add_category,name="add_category"),
    path('delete_category/',views.delete_category,name="delete_category"),
    path('client_user/',views.client_user,name="client_user"),
    path('notification/<int:id>/', views.notification_detail),
    path("client-forgot-password/", views.client_forgot_password, name="client_forgot_password"),
    path(
        "client-reset-password/<uidb64>/<token>/",
        views.client_reset_password,
        name="client_reset_password"
    ),
    path("about_us",views.about_us,name="about_us")
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)