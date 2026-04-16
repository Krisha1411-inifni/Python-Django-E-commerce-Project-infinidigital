import io
import os
import zipfile
from datetime import date

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponseForbidden, FileResponse, HttpResponse, JsonResponse
from django.utils.encoding import force_str, force_bytes
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage, send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings
from django.views.decorators.http import require_POST
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .models import Product, Cart, ClientUser, OrderItem, Order, Category, ProductLesson, LessonProgress, Certificate, \
    ContactMessage
from .tokens import generate_token

# Create your views here.

from django.core.paginator import Paginator

def get_paginated_data(request, queryset, per_page=5, window_size=3):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    current = page_obj.number
    total = paginator.num_pages

    start = current
    end = current + window_size - 1

    # prevent overflow
    if end > total:
        end = total
        start = max(total - window_size + 1, 1)

    page_range = range(start, end + 1)

    return {
        'page_obj': page_obj,
        'page_range': page_range
    }

def index(request):
    categories = Category.objects.all()
    products = Product.objects.all().order_by('-CreationDate')[:8]  # latest 8 products
    allproduct = Product.objects.count
    clients = ClientUser.objects.count
    category = Category.objects.count

    return render(request, 'index.html', {
        "categories": categories,
        "products": products,
        "allproduct": allproduct,
        "clients": clients,
        "category": category
    })

def topic_detail(request, id):


    product = get_object_or_404(Product, id=id)

    client_user_id = request.session.get("client_user_id")
    has_access = False

    if client_user_id:
        client_user = ClientUser.objects.get(id=client_user_id)

        has_access = OrderItem.objects.filter(
            order__client=client_user,
            order__is_paid=True,
            order__is_verified=True,
            product=product
        ).exists()
    # Discount calculation
    if product.ProductDiscountPrice and product.ProductDiscountPrice < product.ProductPrice:
        product.discount_percent = round(
            ((product.ProductPrice - product.ProductDiscountPrice) / product.ProductPrice) * 100
        )
    else:
        product.discount_percent = 0

    lessons = ProductLesson.objects.filter(product=product).order_by("order")

    completed_lessons = []
    course_completed = False

    client_user_id = request.session.get("client_user_id")

    if client_user_id:

        client_user = ClientUser.objects.get(id=client_user_id)

        completed_lessons = LessonProgress.objects.filter(
            user=client_user,
            lesson__product=product,
            completed=True
        ).values_list("lesson_id", flat=True)

        total_lessons = lessons.count()
        completed_count = len(completed_lessons)

        if total_lessons > 0 and total_lessons == completed_count:
            course_completed = True

    context = {
        "product": product,
        "lessons": lessons,
        "completed_lessons": completed_lessons,
        "course_completed": course_completed,
        "has_access": has_access
    }

    return render(request, "topics-detail.html", context)

def complete_lesson(request, lesson_id):

    client_user_id = request.session.get("client_user_id")

    if not client_user_id:
        return redirect("client_signup")

    client = ClientUser.objects.get(id=client_user_id)

    lesson = get_object_or_404(ProductLesson, id=lesson_id)

    LessonProgress.objects.update_or_create(
        user=client,
        lesson=lesson,
        defaults={"completed": True}
    )

    return redirect(f"/course/{lesson.product.id}/?lesson={lesson.id}")

def is_course_completed(user, product):

    total_lessons = ProductLesson.objects.filter(product=product).count()

    completed_lessons = LessonProgress.objects.filter(
        user=user,
        lesson__product=product,
        completed=True
    ).count()

    return total_lessons == completed_lessons

def generate_certificate(user, product):


    filename = f"certificate_{user.id}_{product.id}.pdf"

    certificate_dir = os.path.join(settings.MEDIA_ROOT, "products/certificates")
    os.makedirs(certificate_dir, exist_ok=True)

    filepath = os.path.join(certificate_dir, filename)


    template = finders.find("images/certificate_template.png")
    c = canvas.Canvas(filepath, pagesize=landscape(A4))
    width, height = landscape(A4)

    primary = HexColor("#5a3eea")
    secondary = HexColor("#8b6cff")
    dark = HexColor("#333333")


    # draw background template
    img = ImageReader(template)
    img_width, img_height = img.getSize()

    aspect = img_height / img_width

    # fit image to page width
    new_width = width
    new_height = width * aspect

    # center vertically
    y_position = (height - new_height) / 2

    c.drawImage(template, 0, y_position, width=new_width, height=new_height)
    # USER NAME
    c.setFillColor(secondary)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(width/2, 320, user.first_name+" "+user.last_name)

    # COURSE NAME
    text1 = "has successfully completed a professional training program"
    text2 = product.ProductName
    text3 = f"on {date.today()}"
    text4 = "His / Her dedication and commitment to the learning process are truly commendable."

    c.setFillColor(secondary)
    c.setFont("Helvetica", 14)

    c.drawCentredString(width / 2, 260, text1)
    c.drawCentredString(width / 2, 240, text2)
    c.drawCentredString(width / 2, 220, text3)
    c.drawCentredString(width / 2, 200, text4)

    # Certificate ID
    c.setFillColor(secondary)
    c.setFont("Helvetica", 12)
    c.drawRightString(width - 80, 60, f"Certificate ID: {user.id}-{product.id}")

    c.save()

    return f"products/certificates/{filename}"

def download_certificate(request, product_id):

    client_user_id = request.session.get("client_user_id")

    if not client_user_id:
        return redirect("client_signup")

    client = get_object_or_404(ClientUser, id=client_user_id)

    product = Product.objects.get(id=product_id)

    if not is_course_completed(client, product):
        return redirect("topic_detail", product.id)

    cert, created = Certificate.objects.get_or_create(
        user=client,
        product=product
    )

    if not cert.certificate_file:
        path = generate_certificate(client, product)
        cert.certificate_file = path
        cert.save()

    return redirect(cert.certificate_file.url)

def topic_listing(request):
    return render(request,'topic-listing.html')

def our_services(request):
    products = Product.objects.all()
    first_five_products = Product.objects.order_by("-id")[:10]
    return render(request ,'our-services.html',{'products' : products, "firstfive" : first_five_products})

def template(request):
    products = Product.objects.filter(CategoryId__CategoryName="Template")
    return render(request, 'template.html', {'products' : products})

def e_books(request):
    products = Product.objects.filter(CategoryId__CategoryName="E-Books")
    return render(request, 'e_books.html', {'products' : products})

def pdfs(request):
    products = Product.objects.filter(CategoryId__CategoryName="PDFs")
    return render(request, 'pdfs.html', {'products': products})

def source_code(request):
    products = Product.objects.filter(CategoryId__CategoryName="Source Code / Projects")
    return render(request,'source_code.html',{'products': products})

def courses(request):
    products = Product.objects.filter(CategoryId__CategoryName="Courses")
    return render(request,'courses.html',{'products':products})


def search(request):
    query = request.GET.get('q')
    products = Product.objects.all()

    if query:
        products = products.filter(
            Q(ProductName__icontains=query) |
            Q(ShortDescription__icontains=query) |
            Q(LongDescription__icontains=query) |
            Q(CategoryId__CategoryName__icontains=query)
        ).distinct()

    return render(request, 'search.html', {
        'products': products,
        'query': query
    })

def contact(request):
    return render(request,'contact.html')

def category_page(request, id):
    category = get_object_or_404(Category, id=id)

    return render(request, f'products/{category.template_name}', {
        'category': category
    })

from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render


def has_purchased(client, product):
    return  OrderItem.objects.filter(
        order__client=client,
        order__is_paid=True,
        order__is_verified=True,
        product=product
    ).exists()

def add_to_cart(request,product_id):
    client_user_id = request.session.get("client_user_id")

    if not client_user_id:
        messages.warning(request, "Please sign in first.")
        return redirect("client_signup")

    client = get_object_or_404(ClientUser, id=client_user_id)
    product = get_object_or_404(Product, id=product_id)

    # 🔎 1️⃣ Check if already purchased & verified
    verified_order_item = OrderItem.objects.filter(
        order__client=client,
        order__is_paid=True,
        order__is_verified=True,
        product=product
    ).first()

    if verified_order_item:
        messages.info(request, "You already purchased this product.")
        return redirect("my_downloads")

    # 🔎 2️⃣ Check if payment is pending verification
    pending_order_item = OrderItem.objects.filter(
        order__client=client,
        order__is_paid=True,
        order__is_verified=False,
        product=product
    ).first()

    if pending_order_item:
        messages.info(request, "Your payment is under verification.")
        return redirect("payment_pending", order_id=pending_order_item.order.id)

    # 🔎 3️⃣ Prevent duplicate cart entries
    already_in_cart = Cart.objects.filter(user=client, product=product).exists()

    if already_in_cart:
        messages.info(request, "Product already in cart.")
        return redirect("cart")

    # 🟢 Add to cart
    Cart.objects.create(user=client, product=product)
    messages.success(request, "Product added to cart successfully.")

    return redirect("cart")

def cart(request):

    client_user_id = request.session.get("client_user_id")

    if not client_user_id:
        messages.warning(request, "Please sign in first.")
        return redirect("client_signup")

    client = get_object_or_404(ClientUser, id=client_user_id)

    cart_items = Cart.objects.filter(user=client)

    context = {
        "cart_items": cart_items
    }

    return render(request, "cart.html", context)

def remove_from_cart(request, cart_id):
    client_user_id = request.session.get('client_user_id')

    if not client_user_id:
        messages.warning(request, "Please sign in first.")
        return redirect('client_signup')

    client_user = get_object_or_404(ClientUser, id=client_user_id)

    cart_item = get_object_or_404(
        Cart,
        id=cart_id,
        user=client_user
    )

    cart_item.delete()

    # AJAX Support
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})

    messages.success(request, "Product removed from cart.")
    return redirect('cart')

def checkout(request):
    client_user_id = request.session.get('client_user_id')

    if not client_user_id:
        messages.warning(request, "Please sign in first.")
        return redirect('client_signup')

    client_user = get_object_or_404(ClientUser, id=client_user_id)

    buy_now_product_id = request.GET.get('buy_now')

    items = []
    total = 0

    # 🟢 BUY NOW FLOW
    if buy_now_product_id:
        product = get_object_or_404(Product, id=buy_now_product_id)

        # 🔎 Check if already purchased (paid + verified)
        verified_order_item = OrderItem.objects.filter(
            order__client=client_user,
            order__is_paid=True,
            order__is_verified=True,
            product=product
        ).first()

        if verified_order_item:
            messages.info(request, "You already purchased this product.")
            return redirect("my_downloads")

        # 🔎 Check if payment done but verification pending
        pending_order_item = OrderItem.objects.filter(
            order__client=client_user,
            order__is_paid=True,
            order__is_verified=False,
            product=product
        ).first()

        if pending_order_item:
            messages.info(request, "Your payment is under verification.")
            return redirect("payment_pending", order_id=pending_order_item.order.id)

        # 🟢 Continue normal Buy Now flow
        items.append({
            "product": product,
            "price": product.ProductDiscountPrice
        })

        total = product.ProductDiscountPrice

        request.session['checkout_mode'] = 'buy_now'
        request.session['buy_now_product_id'] = product.id
    # 🟢 CART FLOW
    # 🟢 CART FLOW
    else:
        cart_items = Cart.objects.filter(user=client_user)

        if not cart_items.exists():
            messages.warning(request, "Your cart is empty.")
            return redirect('cart')

        for item in cart_items:
            product = item.product

            # ✅ Already verified purchase
            verified_order_item = OrderItem.objects.filter(
                order__client=client_user,
                order__is_paid=True,
                order__is_verified=True,
                product=product
            ).first()

            if verified_order_item:
                messages.info(request, f"You already purchased {product.ProductName}.")
                item.delete()
                continue

            # ⏳ Payment pending
            pending_order_item = OrderItem.objects.filter(
                order__client=client_user,
                order__is_paid=True,
                order__is_verified=False,
                product=product
            ).first()

            if pending_order_item:
                messages.info(request, f"{product.ProductName} payment is under verification.")
                return redirect("payment_pending", order_id=pending_order_item.order.id)

            # 🟢 Safe to checkout
            items.append({
                "product": product,
                "price": product.ProductDiscountPrice
            })

            total += product.ProductDiscountPrice

        if not items:
            return redirect("my_downloads")

        request.session['checkout_mode'] = 'cart'

    return render(request, 'checkout.html', {
        "items": items,
        "total": total,
        "client_user": client_user
    })

def create_order(request):
    client_user_id = request.session.get('client_user_id')

    if not client_user_id or request.method != "POST":
        return redirect('cart')

    client_user = get_object_or_404(ClientUser, id=client_user_id)

    mode = request.session.get('checkout_mode')

    order = Order.objects.create(
        client=client_user,
        total_amount=0,
        is_paid=False
    )

    total = 0

    if mode == 'buy_now':
        product_id = request.session.get('buy_now_product_id')
        product = get_object_or_404(Product, id=product_id)

        OrderItem.objects.create(
            order=order,
            product=product,
            price=product.ProductDiscountPrice
        )

        total = product.ProductDiscountPrice

    elif mode == 'cart':
        cart_items = Cart.objects.filter(user=client_user)

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                price=item.product.ProductDiscountPrice
            )

            total += item.product.ProductDiscountPrice
        cart_items.delete()

    order.total_amount = total
    order.save()
    return redirect('payment', order_id=order.id)

def payment(request, order_id):
    client_user_id = request.session.get('client_user_id')
    if not client_user_id:
        return redirect('client_signup')
    client = get_object_or_404(ClientUser, id=client_user_id)
    order = get_object_or_404(
        Order,
        id=order_id,
        client=client,
        is_paid=False
    )

    if request.method == "POST":
        payment_id = request.POST.get("payment_id")
        order.payment_id = payment_id
        order.payment_provider = "upi"
        order.is_paid = True
        order.save()
        return redirect("payment_pending", order_id=order.id)
    return render(request, "payment.html", {"order": order})

def payment_pending(request, order_id):
    client_user_id = request.session.get('client_user_id')
    if not client_user_id:
        return redirect('client_signup')
    client = get_object_or_404(ClientUser, id=client_user_id)
    order = get_object_or_404(
        Order,
        id=order_id,
        client=client
    )

    return render(request, "payment_pending.html", { "order": order })


def download_product(request, product_id):
    client_user_id = request.session.get('client_user_id')

    if not client_user_id:
        messages.warning(request, "Please sign in first.")
        return redirect('client_signup')

    client = get_object_or_404(ClientUser, id=client_user_id)

    has_access = OrderItem.objects.filter(
        order__client=client,
        order__is_paid=True,
        order__is_verified=True,
        product_id=product_id
    ).exists()

    if not has_access:
        return HttpResponseForbidden("You have not purchased this product.")

    product = get_object_or_404(Product, id=product_id)

    # ✅ success message (will show on next page)
    messages.success(request, "Download started successfully ✅")

    return FileResponse(
        product.ProductFile.open("rb"),
        as_attachment=True,
        filename=os.path.basename(product.ProductFile.name)
    )

def download_zip(request):
    client_user_id = request.session.get("client_user_id")

    if not client_user_id:
        messages.warning(request, "Please sign in first.")
        return redirect("client_signup")

    client = get_object_or_404(ClientUser, id=client_user_id)

    purchased_items = OrderItem.objects.filter(
        order__client=client,
        order__is_paid=True,
        order__is_verified=True
    ).select_related("product")

    # Collect only products that actually have downloadable files
    downloadable_files = []
    for item in purchased_items:
        product = item.product
        if product.ProductFile:  # skip courses
            downloadable_files.append(product)

    # ❗ If only courses exist
    if not downloadable_files:
        messages.info(request, "No downloadable products found. Courses cannot be downloaded as ZIP.")
        return redirect("my_downloads")

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for product in downloadable_files:
            file_path = product.ProductFile.path
            file_name = os.path.basename(product.ProductFile.name)
            zip_file.write(file_path, arcname=file_name)

    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="InfiniDigital.zip"'

    return response
def my_downloads(request):
    client_user_id = request.session.get("client_user_id")

    if not client_user_id:
        messages.warning(request, "Please sign in first.")
        return redirect("client_signup")

    client = get_object_or_404(ClientUser, id=client_user_id)

    purchased_items = OrderItem.objects.filter(
        order__client=client,
        order__is_paid=True,
        order__is_verified=True
    ).select_related("product", "order")

    # 🔹 Get lessons for purchased courses
    lessons = ProductLesson.objects.filter(
        product__in=[item.product for item in purchased_items]
    ).order_by("product", "order")

    return render(request, "my_downloads.html", {
        "purchased_items": purchased_items,
        "lessons": lessons
    })

def course_player(request, product_id):

    client_user_id = request.session.get("client_user_id")

    if not client_user_id:
        return redirect("client_signup")

    client = get_object_or_404(ClientUser, id=client_user_id)

    product = get_object_or_404(Product, id=product_id)

    lesson_id = request.GET.get("lesson")

    if lesson_id:
        current_lesson = ProductLesson.objects.get(id=lesson_id)
    else:
        current_lesson = ProductLesson.objects.filter(product=product).order_by("order").first()


    lessons = ProductLesson.objects.filter(product=product).order_by("order")
    total_lessons = lessons.count()

    completed_count = LessonProgress.objects.filter(
        user=client,
        lesson__product=product,
        completed=True
    ).count()

    progress = int((completed_count / total_lessons) * 100) if total_lessons > 0 else 0

    course_completed = completed_count == total_lessons
    # check purchase
    has_access = OrderItem.objects.filter(
        order__client=client,
        order__is_paid=True,
        order__is_verified=True,
        product=product
    ).exists()

    if not has_access:
        return HttpResponseForbidden("You have not purchased this course.")

    lessons = ProductLesson.objects.filter(product=product).order_by("order")

    completed_lessons = LessonProgress.objects.filter(
        user=client,
        lesson__product=product,
        completed=True
    ).values_list("lesson_id", flat=True)
    total_lessons = lessons.count()
    completed_count = len(completed_lessons)

    progress = int((completed_count / total_lessons) * 100) if total_lessons > 0 else 0
    context = {
        "product": product,
        "lessons": lessons,
        "completed_lessons": completed_lessons,
        "current_lesson": current_lesson,
        "progress": progress,
        "course_completed": course_completed
    }

    return render(request, "course_player.html", context)

def client_signup(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'signup':
            username = request.POST.get('username')
            fname = request.POST.get('')
            lname = request.POST.get('lname')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')

            if ClientUser.objects.filter(username=username).exists():
                messages.error(request, "Username already exists!")
                return redirect('client_signup')

            if ClientUser.objects.filter(email=email).exists():
                messages.error(request, "Email already exists!")
                return redirect('client_signup')

            if ClientUser.objects.filter(phone_number=phone).exists():
                messages.error(request, "Mobile Number already exists!")
                return redirect('client_signup')

            client = ClientUser(
                username=username,
                email=email,
                phone_number=phone,
                password=password,
                first_name=fname,
                last_name=lname
            )
            client.set_password(password)
            client.save()

            subject = "Welcome to infiniDigital!!"
            message = "Hello " + client.first_name + "!! \n" + "Welcome to InfiniDigital!! \nThank you for visiting our website\n. We have also sent you a confirmation email, please confirm your email address. \n\nThanking You\nInfiniDigital"
            from_email = settings.EMAIL_HOST_USER
            to_list = [client.email]
            send_mail(subject, message, from_email, to_list, fail_silently=True)

            current_site = get_current_site(request)

            message2 = render_to_string("email_confirmation.html", {
                'name': client.first_name,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(client.pk)),
                'token': generate_token.make_token(client),
            })

            email = EmailMessage(
                subject="Confirm your email – InfiniDigital",
                body=message2,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[client.email],
            )
            email.content_subtype = "html"
            email.send()

            messages.success(request, "Account created successfully!")
            return redirect('client_signup')

        elif form_type == 'signin':
            username = request.POST.get('username')
            password = request.POST.get('password')

            try:
                client = ClientUser.objects.get(username=username)
            except ClientUser.DoesNotExist:
                messages.error(request, "Invalid credentials!")
                return redirect('client_signup')

            if not client.check_password(password):
                messages.error(request, "Invalid credentials!")
                return redirect('client_signup')

            if not client.is_active:
                messages.error(request, "Please verify your email first.")
                return redirect('client_signup')

            request.session['client_user_id'] = client.id

            messages.success(request, "Welcome Back!")
            return redirect('home')

    return render(request, "signup.html")


def client_activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        client = ClientUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, ClientUser.DoesNotExist):
        client = None

    if client is not None and generate_token.check_token(client, token):

        if client.is_active:
            messages.info(request, "Your account is already activated.")
            return redirect('client_signup')

        client.is_active = True
        client.save()

        request.session['client_user_id'] = client.id

        messages.success(request, "Account activated successfully!")
        return redirect('home')

    messages.error(request, "Activation link is invalid or expired.")
    return render(request, 'activation_failed.html')



def client_signout(request):
    request.session.pop('client_user_id',None)
    messages.success(request, "You have been logged out successfully 👋")
    return redirect('client_signup')


def admin_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('admin_login')

    if not request.user.is_staff:
        messages.error(request, "Unauthorized access!")
        return redirect('admin_login')
    unread_count = Notification.objects.filter(is_read=False).count()
    notifications = Notification.objects.all().order_by('-created_at')[:10]

    total_users = ClientUser.objects.count()
    total_revenue = Order.objects.filter(
        is_paid=True,
        is_verified=True
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    total_orders = Order.objects.count()
    active_users = ClientUser.objects.filter(is_active=True).count()
    print(active_users)
    total_cart_items = Cart.objects.count()
    total_certificates = Certificate.objects.count()
    recent_orders = Order.objects.select_related('client').order_by('-creation_date')[:5]

    recent_orders1 = Order.objects.select_related('client') \
                        .prefetch_related('items__product') \
                        .order_by('-creation_date')[:5]


    categories = Category.objects.all()
    category_counts = []

    for cat in categories:
        count = Product.objects.filter(CategoryId=cat).count()
        category_counts.append({
            "name": cat.CategoryName,
            "count": count
        })

    monthly_revenue = (
        Order.objects.filter(is_paid=True, is_verified=True)
        .annotate(month=TruncMonth('creation_date'))
        .values('month')
        .annotate(total=Sum('total_amount'))
        .order_by('month')
    )
    months = []
    revenues = []

    for item in monthly_revenue:
        months.append(item['month'].strftime("%b"))
        revenues.append(float(item['total']))

    context ={
        "total_users":total_users,
        "total_revenue" : total_revenue,
        "total_orders": total_orders,
        "active_user":active_users,
        "total_cart_items":total_cart_items,
        "total_certificates":total_certificates,
        "recent_orders":recent_orders,
        "recent_orders1":recent_orders1,
        "categories":categories,
        "category_counts":category_counts,
        "months":months,
        "revenues":revenues,
        "unread_count": unread_count,
        "notifications": notifications
    }

    return render(request, 'admin/index.html',context)
    # or dashboard.html

from django.shortcuts import render
from .models import Product, Category

def admin_products(request):
    products = Product.objects.select_related('CategoryId').all()
    categories = Category.objects.all()
    lessons = ProductLesson.objects.all()

    # -------------------
    # FILTERS
    # -------------------
    category_id = request.GET.get('category')
    search_query = request.GET.get('search')
    sort = request.GET.get('sort')

    if category_id:
        products = products.filter(CategoryId_id=category_id)

    if search_query:
        products = products.filter(ProductName__icontains=search_query)

    # -------------------
    # SORTING
    # -------------------
    sort_options = {
        'asc': 'id',
        'desc': '-id',
        'price_low': 'ProductPrice',
        'price_high': '-ProductPrice',
        'name_az': 'ProductName',
        'name_za': '-ProductName',
    }

    if sort in sort_options:
        products = products.order_by(sort_options[sort])

    # -------------------
    # PAGINATION
    # -------------------
    data = get_paginated_data(request, products, per_page=5, window_size=3)

    context = {
        'products': data['page_obj'],
        'page_range': data['page_range'],
        'categories': categories,
        'current_sort': sort,
        'current_category': category_id,
        'search_query': search_query,
    }

    return render(request, 'admin/product.html', context)

from django.shortcuts import render, redirect
from .models import Product, ProductLesson, Category

def add_product(request):
    if request.method == "POST":
        try:
            product_id = request.POST.get("product_id")
            print("PRODUCT ID : ", request.POST.get("product_id"))

            category_id = request.POST.get("category")
            category = Category.objects.get(id=category_id)

            # =========================
            # EDIT MODE
            # =========================
            if product_id:
                product = Product.objects.get(id=product_id)

                product.CategoryId = category
                product.ProductName = request.POST.get("ProductName")
                product.ShortDescription = request.POST.get("ShortDescription")
                product.ProductPrice = request.POST.get("productprice")
                product.ProductDiscountPrice = request.POST.get("discountprice") or None
                product.LongDescription = request.POST.get("LongDescription")

                product.ProgrammingLanguage = request.POST.get("ProgrammingLanguage")
                product.Framework = request.POST.get("Framework")
                product.Database = request.POST.get("Database")
                product.Platform = request.POST.get("Platform")
                product.SoftwareRequirements = request.POST.get("SoftwareRequirements")

                product.Features = request.POST.get("Features")
                product.FilesIncluded = request.POST.get("FilesIncluded")

                # ✅ FILES (only update if uploaded)
                if request.FILES.get("ProductImage1"):
                    product.ProductImage1 = request.FILES.get("ProductImage1")

                if request.FILES.get("ProductImage2"):
                    product.ProductImage2 = request.FILES.get("ProductImage2")

                if request.FILES.get("ProductImage3"):
                    product.ProductImage3 = request.FILES.get("ProductImage3")

                if request.FILES.get("ProductFile"):
                    product.ProductFile = request.FILES.get("ProductFile")

                if request.FILES.get("DemoVideo"):
                    product.DemoVideo = request.FILES.get("DemoVideo")

                product.save()

                # ✅ DELETE OLD LESSONS (important)
                ProductLesson.objects.filter(product=product).delete()

                messages.success(request, "Product updated successfully")

            # =========================
            # ADD MODE
            # =========================
            else:
                product = Product.objects.create(
                    CategoryId=category,
                    ProductName=request.POST.get("ProductName"),
                    ShortDescription=request.POST.get("ShortDescription"),
                    ProductPrice=request.POST.get("productprice"),
                    ProductDiscountPrice=request.POST.get("discountprice") or None,
                    LongDescription=request.POST.get("LongDescription"),

                    ProductImage1=request.FILES.get("ProductImage1"),
                    ProductImage2=request.FILES.get("ProductImage2"),
                    ProductImage3=request.FILES.get("ProductImage3"),

                    ProductFile=request.FILES.get("ProductFile"),
                    PreviewFile=request.FILES.get("PreviewFile"),
                    DemoVideo=request.FILES.get("DemoVideo"),

                    ProgrammingLanguage=request.POST.get("ProgrammingLanguage"),
                    Framework=request.POST.get("Framework"),
                    Database=request.POST.get("Database"),
                    Platform=request.POST.get("Platform"),
                    SoftwareRequirements=request.POST.get("SoftwareRequirements"),

                    Features=request.POST.get("Features"),
                    FilesIncluded=request.POST.get("FilesIncluded"),
                )

                messages.success(request, "Product added successfully")

            # =========================
            # LESSONS (COMMON)
            # =========================
            index = 0
            while True:
                title_key = f"lesson_title_{index}"
                video_key = f"lesson_video_{index}"

                if title_key not in request.POST:
                    break

                title = request.POST.get(title_key)
                video = request.FILES.get(video_key)
                preview = request.POST.get(f"lesson_preview_{index}") == "on"

                if title:  # avoid empty lessons
                    ProductLesson.objects.create(
                        product=product,
                        title=title,
                        video=video,
                        is_preview=preview,
                        order=index
                    )

                index += 1

            return redirect("admin_products")


        except Exception as e:

            print("ERROR:", e)

            messages.error(request, "Something went wrong while saving product")

            return redirect("admin_products")

    categories = Category.objects.all()
    return render(request, "admin/products.html", {"categories": categories})

@require_POST
def delete_product(request):
    product_id = request.POST.get("id")

    if not product_id:
        return JsonResponse({"success": False, "error": "No ID provided"})

    try:
        product = Product.objects.get(id=product_id)
        name = product.ProductName
        product.delete()

        return JsonResponse({
            "success": True,
            "name": name,
            "id": product_id
        })

    except Product.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Product not found"
        })

def admin_register(request):
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not username:
            return JsonResponse({"success": False, "error": "Username required"})

        if not email:
            return JsonResponse({"success": False, "error": "Email required"})

        # ✅ EDIT
        if user_id:
            user = User.objects.get(id=user_id)
            user.username = username
            user.email = email

            if password:
                if password != confirm_password:
                    return JsonResponse({"success": False, "error": "Passwords do not match"})
                user.set_password(password)

            user.save()

            return JsonResponse({
                "success": True,
                "message": f"User {username} updated successfully",
                "id": user.id,
                "username": user.username,
                "email": user.email
            })

        # ✅ CREATE
        if User.objects.filter(username=username).exists():
            return JsonResponse({"success": False, "error": "Username exists"})

        if User.objects.filter(email=email).exists():
            return JsonResponse({"success": False, "error": "Email exists"})

        if password != confirm_password:
            return JsonResponse({"success": False, "error": "Passwords do not match"})

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        user.is_staff = True
        user.is_superuser = True
        user.save()

        return JsonResponse({
            "success": True,
            "message": f"User {username} created successfully",
            "id": user.id,
            "username": user.username,
            "email": user.email
        })

    return JsonResponse({"success": False, "error": "Invalid request"})

def admin_activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user is not None and generate_token.check_token(user, token):

        if user.is_active:
            messages.info(request, "Account already activated.")
            return redirect('admin_login')

        user.is_active = True
        user.save()

        login(request, user)  # Django session

        messages.success(request, "Admin account activated!")
        return redirect('admin_dashboard')

    return render(request, "register.html")

def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Invalid credentials!")
            return redirect('admin_login')

        if not user.is_active:
            messages.error(request, "Please verify your email first.")
            return redirect('admin_login')

        if not user.is_staff:
            messages.error(request, "Not authorized as admin.")
            return redirect('admin_login')

        login(request, user)  # session handled automatically

        messages.success(request, "Welcome Admin!")
        return redirect('admin_dashboard')

    return render(request, "admin/login.html")

def admin_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully 👋")
    return redirect('admin_login')

def admin_users(request):
    admin_users = User.objects.all()
    sort = request.GET.get('sort')
    # -------------------
    # SORTING
    # -------------------
    sort_options = {
        'asc': 'id',
        'desc': '-id',
        'name_az': 'username',
        'name_za': '-username',
    }

    if sort in sort_options:
        admin_users = User.objects.order_by(sort_options[sort])

    context ={
        "admin_user" : admin_users,
        'current_sort': sort,
    }
    return render(request,"admin/admin_users.html",context)

@require_POST
def delete_user(request):
    user_id = request.POST.get("id")

    if not user_id:
        return JsonResponse({"success": False, "error": "No ID provided"})

    try:
        user = User.objects.get(id=user_id)
        name = user.username
        user.delete()

        return JsonResponse({
            "success": True,
            "name": name,
            "id": user_id
        })

    except Product.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "User not found"
        })


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({
                "success": False,
                "error": "Email not found"
            })

        current_site = get_current_site(request)

        message = render_to_string("admin/password_reset_email.html", {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': generate_token.make_token(user),
        })

        email = EmailMessage(
            subject="Reset Your Password",
            body=message,
            to=[user.email],
        )
        email.content_subtype = "html"
        email.send()

        return JsonResponse({
            "success": True,
            "message": "Password reset link sent to your email"
        })

    return render(request, "admin/forgot_password.html")

from django.http import JsonResponse

def reset_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user and generate_token.check_token(user, token):
        if request.method == "POST":
            password = request.POST.get("password")
            confirm = request.POST.get("confirm_password")

            if password != confirm:
                return JsonResponse({
                    "success": False,
                    "error": "Passwords do not match"
                })

            user.set_password(password)
            user.save()

            return JsonResponse({
                "success": True,
                "message": "Password reset successful"
            })

        return render(request, "admin/reset_password.html",{"valid": True})

    return render(request, "admin/reset_invalid.html",{"valid": False})

def admin_orders(request):
    orders = Order.objects.select_related('client') \
                         .prefetch_related('items__product') \
                         .order_by('-creation_date')
    sort = request.GET.get('sort')

    sort_options = {
        'asc': 'id',
        'desc': '-id',
        'price_low': 'total_amount',
        'price_high': '-total_amount',
        'paid_first': '-is_paid',
        'unpaid_first': 'is_paid',
        'pending': 'is_verified',
        'verified': '-is_verified',
    }

    if sort in sort_options:
        orders = orders.order_by(sort_options[sort])

    data = get_paginated_data(request, orders, per_page=5, window_size=3)
    context = {
        'orders': data['page_obj'],
        'page_range': data['page_range'],
        'current_sort': sort,
    }
    return render(request,"admin/orders.html",context)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Order

@csrf_exempt
def verify_order(request):
    if request.method == "POST":
        order_id = request.POST.get("order_id")

        try:
            order = Order.objects.select_related('client').prefetch_related('items__product').get(id=order_id)

            # Mark as verified
            order.is_verified = True
            order.save()

            # ✅ Get product names
            items = order.items.all()
            product_list = ", ".join([item.product.ProductName for item in items])

            # ✅ Email content
            subject = "Your Order Has Been Verified ✅"
            message = f"""
Hello {order.client.first_name},

Your order (ID: {order.id}) has been successfully verified.

Products:
{product_list}

Thank you for purchasing from InfiniDigital 🚀

Regards,
InfiniDigital Team
            """

            # ✅ Send email
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [order.client.email],
                fail_silently=False,
            )

            return JsonResponse({
                "success": True,
                "message": "Order verified and email sent"
            })

        except Order.DoesNotExist:
            return JsonResponse({
                "success": False,
                "error": "Order not found"
            })

    return JsonResponse({"error": "Invalid request"})

def admin_category(request):
    categorys = Category.objects.all()
    sort = request.GET.get('sort')

    sort_options = {
        'asc': 'id',
        'desc': '-id',
        'name_az':'CategoryName',
        'name_za':'-CategoryName'
    }

    if sort in sort_options:
        categorys = categorys.order_by(sort_options[sort])

    data = get_paginated_data(request, categorys, per_page=5, window_size=3)
    context = {
        'categorys': data['page_obj'],
        'page_range': data['page_range'],
        'current_sort': sort,
    }
    return render(request,"admin/admin_category.html",context)

def add_category(request):
    if request.method == "POST":
        category_id = request.POST.get("category_id")
        categoryname = request.POST.get("CategoryName", "").strip()
        categorydescription = request.POST.get("CategoryDescription", "").strip()
        print(categoryname)

        if not categoryname:
            return JsonResponse({"success": False, "error": "CategoryName required"})


        # ✅ EDIT
        if category_id:
            category = Category.objects.get(id=category_id)
            category.CategoryName = categoryname
            category.CategoryDescription = categorydescription

            category.save()

            return JsonResponse({
                "success": True,
                "message": f"User {categoryname} updated successfully",
                "id": category.id,
                "categoryname": category.CategoryName,
                "categorydescription": category.CategoryDescription
            })

        # ✅ CREATE
        if Category.objects.filter(CategoryName=categoryname).exists():
            return JsonResponse({"success": False, "error": "CategoryName exists"})


        category = Category.objects.create(
            CategoryName=categoryname,
            CategoryDescription = categorydescription
        )

        category.save()

        return JsonResponse({
            "success": True,
            "message": f" {categoryname} created successfully",
            "id": category.id,
            "categoryname": category.CategoryName,
            "categorydescription": category.CategoryDescription
        })

    return JsonResponse({"success": False, "error": "Invalid request"})

@require_POST
def delete_category(request):
    category_id = request.POST.get("id")

    if not category_id:
        return JsonResponse({"success": False, "error": "No ID provided"})

    try:
        category = Category.objects.get(id=category_id)
        name = category.CategoryName
        category.delete()

        return JsonResponse({
            "success": True,
            "name": name,
            "id": category_id
        })

    except Product.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Category not found"
        })

def client_user(request):
    clients = ClientUser.objects.all()
    sort = request.GET.get('sort')

    sort_options = {
        'asc': 'id',
        'desc': '-id',
    }

    if sort in sort_options:
        clients = ClientUser.objects.order_by(sort_options[sort])

    data = get_paginated_data(request, clients, per_page=5, window_size=3)

    context = {
        'clients': data['page_obj'],
        'page_range': data['page_range'],
        'current_sort': sort,
    }
    return render(request,"admin/client_user.html",context)

from .models import ContactMessage, Notification

def contact_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        # Save contact
        contact = ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )

        # 🔥 CREATE NOTIFICATION
        Notification.objects.create(
            title=f"New Contact from {name}",
            sender_name=name,
            sender_email=email,
            subject=subject,
            message=message
        )

        messages.success(request, "Message sent 🚀")
        return redirect("contact")

    return render(request, "contact.html")

def notification_detail(request, id):
    notif = Notification.objects.get(id=id)
    notif.is_read = True
    notif.save()

    data = {
        "sender_email": notif.sender_email,
        "sender": notif.sender_name,
        "message": notif.message,
        "date": notif.created_at.strftime("%Y-%m-%d %H:%M"),
    }

    return JsonResponse(data)

def client_forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        try:
            user = ClientUser.objects.get(email=email)
        except ClientUser.DoesNotExist:
            messages.error(request, "Email not found")
            return redirect('client_forgot_password')

        current_site = get_current_site(request)

        message = render_to_string("client_password_reset_email.html", {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': generate_token.make_token(user),
        })

        email = EmailMessage(
            subject="Reset Your Password",
            body=message,
            to=[user.email],
        )
        email.content_subtype = "html"
        email.send()

        messages.success(request, "Password reset link sent to your email")
        return redirect('client_forgot_password')

    return render(request, "client_forgot_password.html")

def client_reset_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = ClientUser.objects.get(pk=uid)
    except:
        user = None

    if user and generate_token.check_token(user, token):
        if request.method == "POST":
            password = request.POST.get("password")
            confirm = request.POST.get("confirm_password")

            if password != confirm:
                messages.error(request, "Passwords do not match")
                return redirect(request.path)

            user.set_password(password)
            user.save()

            messages.success(request, "Password reset successful")
            return redirect('client_signup')

        return render(request, "client_reset_password.html", {
            "uid": uidb64,
            "token": token
        })

    return render(request, "reset_invalid.html",{"valid": False})

def about_us(requst):
    return render(requst,"about_us.html")