import io
import os
import zipfile

from django.db.models import Q
from django.http import HttpResponseForbidden, FileResponse, HttpResponse, JsonResponse
from django.utils.encoding import force_str, force_bytes
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage, send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings

from .models import Product, Cart, ClientUser, OrderItem, Order, Category
from .tokens import generate_token

# Create your views here.

def index(request):
    categorys = Category.objects.all()
    return render(request,'index.html',{"categorys" : categorys})

def topic_detail(request,id):
    product = Product.objects.get(id = id)
    product.discount_percent = round(
        ((product.ProductPrice - product.ProductDiscountPrice)
         / product.ProductPrice) * 100
    )

    return render(request,'topics-detail.html',{"product":product})

def topic_listing(request):
    return render(request,'topic-listing.html')

def our_services(request):
    products = Product.objects.all()
    first_five_products = Product.objects.order_by("-id")[:5]
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
    return render(request,'source_code.html')

def courses(request):
    return render(request,'courses.html')

def tools(request):
    return render(request,'tools.html')
from django.db.models import Q

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


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Cart, Product

from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render


def has_purchased(client, product):
    return  OrderItem.objects.filter(
        order__client=client,
        order__is_paid=True,
        order__is_verified=True,
        product=product
    ).exists()

def cart(request):
    client_user_id = request.session.get("client_user_id")

    if not client_user_id:
        messages.warning(request, "Please sign in first.")
        return redirect("client_signup")

    product_id = request.GET.get("product_id")
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
    purchased_items = OrderItem.objects.filter( order__client=client, order__is_paid=True, order__is_verified=True ).select_related("product")
    if not purchased_items.exists():
        return HttpResponseForbidden("No purchased products.")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for item in purchased_items:
            product = item.product
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
    return render(request, "my_downloads.html", { "purchased_items": purchased_items })

def client_signup(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'signup':
            username = request.POST.get('username')
            fname = request.POST.get('fname')
            lname = request.POST.get('lname')
            email = request.POST.get('email')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')

            if ClientUser.objects.filter(username=username).exists():
                messages.error(request, "Username already exists!")
                return redirect('client_signup')

            if ClientUser.objects.filter(email=email).exists():
                messages.error(request, "Email already exists!")
                return redirect('client_signup')

            if password != confirm_password:
                messages.error(request, "Passwords do not match!")
                return redirect('client_signup')

            client = ClientUser(
                username=username,
                email=email,
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

