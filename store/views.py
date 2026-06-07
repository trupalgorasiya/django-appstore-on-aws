from django.shortcuts import render
import re
from django.core.paginator import Paginator
from django.utils.text import slugify
from .utils import *
import razorpay
import random
from datetime import datetime, date
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth.hashers import check_password
from .models import *
from django.shortcuts import render, redirect, get_object_or_404
# Create your views here.
from decimal import Decimal
from django.db.models import Sum
from .models import Product, Category, OrderItem

def home(request):
    categories = Category.objects.all()

    # Get top 3 best selling products
    best_sellers = (
        OrderItem.objects
        .values('product')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:3]
    )

    # Get actual product objects
    product_ids = [item['product'] for item in best_sellers]
    best_products = Product.objects.filter(id__in=product_ids)

    # Keep order same as total_sold
    best_products = sorted(
        best_products,
        key=lambda p: product_ids.index(p.id)
    )

    return render(request, 'home.html', {
        'categories': categories,
        'best_products': best_products
    })

def about(request):
    return render(request, 'about.html')
def faqs(request):
    return render(request, 'faqs.html') 
def category_detail(request, id):
    categories = Category.objects.all()
    category = get_object_or_404(Category, category_id=id)

    products = category.products.all()   # 👈 GET PRODUCTS OF THIS CATEGORY

    return render(request, "category_detail.html", {
        'category': category,
        'categories': categories,
        'products': products   # 👈 SEND PRODUCTS TO TEMPLATE
    })
def registration(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        dob_date = request.POST.get('dob')
        email_id = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        contact_no = request.POST.get('mobile')
        address = request.POST.get('address')

        if User.objects.filter(email_id=email_id).exists():
            messages.error(request, "Email already registered.")
            return redirect('registration')

        error_messages = []
        is_valid = True

        # ✅ Full Name Validation
        if not first_name:
            is_valid = False
            error_messages.append("Full Name is required.")

        # ✅ DOB Required + Age + Future Date Validation
        if not dob_date:
            is_valid = False
            error_messages.append("Date of Birth is required.")
        else:
            try:
                dob = datetime.strptime(dob_date, "%Y-%m-%d").date()

                # Future date check
                if dob > date.today():
                    is_valid = False
                    error_messages.append("Date of Birth cannot be in the future.")

                else:
                    today = date.today()
                    age = today.year - dob.year - (
                        (today.month, today.day) < (dob.month, dob.day)
                    )

                    # Minimum 18 years validation
                    if age < 18:
                        is_valid = False
                        error_messages.append("You must be at least 18 years old to register.")

            except ValueError:
                is_valid = False
                error_messages.append("Invalid Date of Birth format.")

        # ✅ Password Validation
        if password != confirm_password:
            is_valid = False
            error_messages.append("Passwords do not match.")

        if len(password) < 8:
            is_valid = False
            error_messages.append("Password must be at least 8 characters.")

        # ✅ Mobile Validation
        if len(contact_no) != 10 or not contact_no.isdigit():
            is_valid = False
            error_messages.append("Enter valid 10-digit mobile number.")

        # ✅ Address Validation
        if not address:
            is_valid = False
            error_messages.append("Address is required.")

        # ==========================
        # IF ALL VALID
        # ==========================

        if is_valid:
            otp = str(random.randint(100000, 999999))

            request.session['otp'] = otp
            request.session['temp_user'] = {
                'first_name': first_name,
                'dob_date': dob_date,
                'email_id': email_id,
                'password': password,
                'contact_no': contact_no,
                'address': address
            }

            subject = "Verify Your Account - JVJ Enterprise"

            html_content = render_to_string(
                "emails/otp_verification.html",
                {"otp": otp}
            )

            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject,
                text_content,
                settings.EMAIL_HOST_USER,
                [email_id]
            )

            email.attach_alternative(html_content, "text/html")
            email.send()

            messages.success(request, "OTP sent to your email.")
            return redirect('verify_otp')

        # Show all errors
        for msg in error_messages:
            messages.error(request, msg)

    return render(request, 'registration.html')
def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        saved_otp = request.session.get('otp')

        if entered_otp == saved_otp:
            temp_user = request.session.get('temp_user')

            user = User(
                first_name=temp_user['first_name'],
                dob_date=temp_user['dob_date'],
                email_id=temp_user['email_id'],
                password=make_password(temp_user['password']),
                contact_no=temp_user['contact_no'],
                address=temp_user['address']
            )
            user.save()

            del request.session['otp']
            del request.session['temp_user']

            messages.success(request, "Registration successful!")
            return redirect('login')

        else:
            messages.error(request, "Invalid OTP.")

    return render(request, 'verify_otp.html')
def login_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = User.objects.filter(email_id=email).first()

        if user and check_password(password, user.password):
            request.session['user_id'] = user.user_id
            request.session['user_name'] = user.first_name
            messages.success(request, f"Welcome {user.first_name}!")
            return redirect('home')
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "login.html")
def logout_view(request):
    request.session.flush()
    messages.success(request, "Logged out successfully.")
    return redirect('home')
def change_password(request):
    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(request, "Please login first.")
        return redirect('login')

    user = User.objects.filter(user_id=user_id).first()

    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not check_password(current_password, user.password):
            messages.error(request, "Current password is incorrect.")
            return render(request, 'change_password.html')

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'change_password.html')

        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, 'change_password.html')

        user.password = make_password(new_password)
        user.save()

        request.session.flush()
        messages.success(request, "Password updated. Please login again.")
        return redirect('login')

    return render(request, 'change_password.html')
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = User.objects.filter(email_id=email).first()

        if not user:
            messages.error(request, "Email not found.")
            return redirect("forgot_password")

        otp = str(random.randint(100000, 999999))

        request.session["reset_email"] = email
        request.session["reset_otp"] = otp

        subject = "Reset Your Password - JVJ Enterprise"

        html_content = render_to_string(
            "emails/reset_password_otp.html",
            {"otp": otp}
        )

        text_content = strip_tags(html_content)

        email_message = EmailMultiAlternatives(
            subject,
            text_content,
            settings.EMAIL_HOST_USER,
            [email]
        )

        email_message.attach_alternative(html_content, "text/html")
        email_message.send()

        messages.success(request, "OTP sent to your email.")
        return redirect("verify_reset_otp")

    return render(request, "forgot_password.html")
def verify_reset_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        stored_otp = request.session.get("reset_otp")

        if entered_otp == stored_otp:
            request.session["otp_verified"] = True
            return redirect("reset_password")
        else:
            messages.error(request, "Invalid OTP.")

    return render(request, "verify_reset_otp.html")
def reset_password(request):
    if not request.session.get("otp_verified"):
        return redirect("forgot_password")

    if request.method == "POST":
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, "reset_password.html")

        email = request.session.get("reset_email")
        user = User.objects.filter(email_id=email).first()

        user.password = make_password(password)
        user.save()

        request.session.flush()
        messages.success(request, "Password updated successfully.")
        return redirect("login")

    return render(request, "reset_password.html")
def user_details(request):
    user_id = request.session.get("user_id")

    if not user_id:
        return redirect("login")

    user = get_object_or_404(User, user_id=user_id)

    return render(request, "user_details.html", {"user": user})

def edit_profile(request):
    user_id = request.session.get("user_id")

    if not user_id:
        return redirect("login")

    user = get_object_or_404(User, user_id=user_id)

    if request.method == "POST":
        user.first_name = request.POST.get("name")
        user.contact_no = request.POST.get("phone")
        user.address = request.POST.get("address")
        user.dob_date = request.POST.get("dob")

        user.save()

        return redirect("user_details")

    return render(request, "edit_profile.html", {"user": user})

def product_list(request, id):
    categories = Category.objects.all()  # for header menu
    category = get_object_or_404(Category, category_id=id)

    products = category.products.all()

    return render(request, "product_list.html", {
        'category': category,
        'categories': categories,
        'products': products
    })
from django.shortcuts import render, redirect
from django.db.models import Avg
from django.contrib import messages
from .models import Product, Review, OrderItem, User

def product_detail(request, id):
    product = Product.objects.get(id=id)
    user_id = request.session.get('user_id')
    images = product.images.all()

    reviews = Review.objects.filter(product=product).order_by('-created_at')

    average_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    average_rating = round(average_rating, 1)

    total_reviews = reviews.count()

    rating_counts = {
        5: reviews.filter(rating=5).count(),
        4: reviews.filter(rating=4).count(),
        3: reviews.filter(rating=3).count(),
        2: reviews.filter(rating=2).count(),
        1: reviews.filter(rating=1).count(),
    }

    stars = [5, 4, 3, 2, 1]

    has_ordered = False
    user_reviewed = False

    if user_id:
        has_ordered = OrderItem.objects.filter(
            order__user__user_id=user_id,
            product=product,
            order__status="Completed"
        ).exists()

        user_reviewed = Review.objects.filter(
            product=product,
            user__user_id=user_id
        ).exists()

    if request.method == "POST" and has_ordered and not user_reviewed:
        rating = int(request.POST.get('rating'))
        comment = request.POST.get('comment')

        user = User.objects.get(user_id=user_id)

        Review.objects.create(
            product=product,
            user=user,
            rating=rating,
            comment=comment
        )

        messages.success(request, "Review submitted successfully!")
        return redirect('product_detail', id=product.id)

    context = {
        "product": product,
        "reviews": reviews,
        "average_rating": average_rating,
        "total_reviews": total_reviews,
        "rating_counts": rating_counts,
        "stars": stars,
        "has_ordered": has_ordered,
        "user_reviewed": user_reviewed,
        "images":images,
    }

    return render(request, "product_detail.html", context)

def category_products(request, id):
    category = get_object_or_404(Category, category_id=id)
    products = Product.objects.filter(category=category)
    categories = Category.objects.all()  # for header dropdown

    return render(request, 'product_list.html', {
        'category': category,
        'products': products,
        'categories': categories
    })

from django.contrib import messages
from django.shortcuts import redirect
from .models import Wishlist, Product

# Add to wishlist
def add_to_wishlist(request, product_id):
    if not request.session.get('user_id'):
        messages.error(request, "Please login first.")
        return redirect('login')

    user = User.objects.get(user_id=request.session['user_id'])
    product = Product.objects.get(id=product_id)

    if Wishlist.objects.filter(user=user, product=product).exists():
        messages.warning(request, "Product already added to wishlist.")
    else:
        Wishlist.objects.create(user=user, product=product)
        messages.success(request, "Product added to wishlist successfully.")

    return redirect('wishlist')


# Wishlist page
def wishlist_page(request):
    if not request.session.get('user_id'):
        return redirect('login')

    user = User.objects.get(user_id=request.session['user_id'])
    wishlist_items = Wishlist.objects.filter(user=user)

    return render(request, 'wishlist.html', {
        'wishlist_items': wishlist_items
    })



# Remove from wishlist
def remove_from_wishlist(request, product_id):
    user = User.objects.get(user_id=request.session['user_id'])
    product = Product.objects.get(id=product_id)

    Wishlist.objects.filter(user=user, product=product).delete()
    messages.success(request, "Product removed from wishlist.")

    return redirect('wishlist')


# ADD TO CART
def add_to_cart(request, product_id):
    if not request.session.get('user_id'):
        messages.error(request, "Please login first.")
        return redirect('login')

    user = User.objects.get(user_id=request.session['user_id'])
    product = get_object_or_404(Product, id=product_id)

    cart_item, created = Cart.objects.get_or_create(user=user, product=product)

    if not created:
        if cart_item.quantity < product.stock:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, "Quantity updated in cart.")
        else:
            messages.warning(request, "Stock limit reached.")
    else:
        messages.success(request, "Product added to cart.")

    return redirect('cart')


# CART PAGE
def cart_page(request):
    if not request.session.get('user_id'):
        return redirect('login')

    user = User.objects.get(user_id=request.session['user_id'])
    cart_items = Cart.objects.filter(user=user)

    subtotal = sum(item.subtotal() for item in cart_items)
    CGST_RATE = Decimal('0.025')
    SGST_RATE = Decimal('0.025')

    cgst = subtotal * CGST_RATE
    sgst = subtotal * SGST_RATE

    total = subtotal + cgst + sgst

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'cgst': cgst,
        'sgst':sgst,
        'total': total
    })


# UPDATE CART
def update_cart(request, product_id, action):
    if not request.session.get('user_id'):
        return redirect('login')

    user = User.objects.get(user_id=request.session['user_id'])
    product = get_object_or_404(Product, id=product_id)
    cart_item = Cart.objects.get(user=user, product=product)

    if action == "increase":
        if cart_item.quantity < product.stock:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, "Quantity increased successfully.")
        else:
            messages.error(request, "Cannot add more. Stock limit reached.")

    elif action == "decrease":
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
            messages.info(request, "Quantity decreased.")
        else:
            messages.warning(request, "Minimum quantity is 1.")

    return redirect('cart')


# REMOVE ITEM
def remove_cart(request, product_id):
    user = User.objects.get(user_id=request.session['user_id'])
    product = get_object_or_404(Product, id=product_id)

    Cart.objects.filter(user=user, product=product).delete()
    messages.success(request, "Item removed from cart.")

    return redirect('cart')

def checkout_page(request):

    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    
    user = User.objects.get(user_id=user_id)
    cart_items = Cart.objects.filter(user=user)

    if not cart_items:
        return redirect('cart')

    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    CGST_RATE = Decimal('0.025')
    SGST_RATE = Decimal('0.025')

    cgst = subtotal * CGST_RATE
    sgst = subtotal * SGST_RATE
    total = subtotal + cgst + sgst
    COD_LIMIT = Decimal('50000')
    if request.method == "POST":

        payment_method = request.POST.get('payment')
        main_address = request.POST.get('main_address')
        new_address = request.POST.get('new_address')
        different_address = request.POST.get('different_address')

        if different_address:
            address = new_address
        else:
            address = main_address
        if different_address and not new_address:
            messages.error(request, "Please enter new shipping address.")
            return redirect("checkout")
        # 🔥 ONLINE PAYMENT
        if payment_method == "ONLINE":

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

            razorpay_order = client.order.create({
                "amount": int(total * 100),  # Razorpay works in paisa
                "currency": "INR",
                "payment_capture": 1
            })
            request.session['razorpay_order_id'] = razorpay_order["id"]
            request.session['checkout_address'] = address
            return render(request, "razorpay_payment.html", {
                "razorpay_order_id": razorpay_order["id"],
                "razorpay_key": settings.RAZORPAY_KEY_ID,
                "amount": int(total * 100),
                "user": user,
                "address": address,
            })

        # 🔥 COD
        elif payment_method == "COD":

            if total > COD_LIMIT:
                messages.error(request, "Cash On Delivery is not available for orders above ₹50,000.")
                return redirect("checkout")

            order = Order.objects.create(
                user=user,
                full_name=user.first_name,
                email=user.email_id,
                phone=user.contact_no,
                address=address,
                payment_method="COD",
                subtotal=subtotal,
                cgst=cgst,
                sgst=sgst,
                total=total
            )

            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price,
                    warranty_years=item.product.warranty_years
                )

                item.product.stock -= item.quantity
                item.product.save()

            cart_items.delete()
            send_order_confirmation_email(order)
            return redirect('order_success', order.id)

    return render(request, "checkout.html", {
        "cart_items": cart_items,
        "subtotal": subtotal,
        "cgst":cgst,
        "sgst":sgst,
        "total": total,
        "user": user
    })

def order_success(request, order_id):
    order = Order.objects.get(id=order_id)
    return render(request, 'order_success.html', {'order': order})

def payment_success(request):

    payment_id = request.GET.get("payment_id")
    razorpay_order_id = request.session.get("razorpay_order_id")
    address = request.session.get("checkout_address")

    user_id = request.session.get('user_id')
    user = User.objects.get(user_id=user_id)

    cart_items = Cart.objects.filter(user=user)

    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    CGST_RATE = Decimal('0.025')
    SGST_RATE = Decimal('0.025')

    cgst = subtotal * CGST_RATE
    sgst = subtotal * SGST_RATE
    total = subtotal + cgst + sgst

    # 🔥 Create Order with Razorpay IDs
    order = Order.objects.create(
        user=user,
        full_name=user.first_name,
        email=user.email_id,
        phone=user.contact_no,
        address=address,
        payment_method="ONLINE",
        subtotal=subtotal,
        cgst=cgst,
        sgst=sgst,
        total=total,
        razorpay_payment_id=payment_id,
        razorpay_order_id=razorpay_order_id
    )

    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price,
            warranty_years=item.product.warranty_years
        )

        item.product.stock -= item.quantity
        item.product.save()

    cart_items.delete()
    send_order_confirmation_email(order)
    # Clear session
    request.session.pop("razorpay_order_id", None)
    request.session.pop("checkout_address", None)

    return redirect("order_success", order.id)



def order_history(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    user = User.objects.get(user_id=user_id)

    orders_list = Order.objects.filter(user=user).order_by('-created_at')

    paginator = Paginator(orders_list, 5)  # 5 orders per page
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)

    return render(request, "order_history.html", {
        "orders": orders
    })

def order_detail(request, order_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    user = User.objects.get(user_id=user_id)

    order = Order.objects.filter(id=order_id, user=user).first()
    if not order:
        return redirect('order_history')

    order_items = order.items.all()

    return render(request, "order_detail.html", {
        "order": order,
        "order_items": order_items
    })
def track_order(request, order_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    user = User.objects.get(user_id=user_id)

    order = Order.objects.filter(id=order_id, user=user).first()
    if not order:
        return redirect('order_history')

    return render(request, "track_order.html", {
        "order": order
    })

from datetime import date, timedelta
from django.shortcuts import render, redirect
from .models import OrderItem

def my_warranties(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    today = date.today()

    # Get completed orders only with warranty
    items = OrderItem.objects.filter(
        order__user__user_id=user_id,
        order__status="Completed",
        warranty_years__gt=0
    ).select_related('order', 'product')

    warranty_data = []

    for item in items:
        order_date = item.order.created_at.date()
        expiry_date = order_date.replace(year=order_date.year + item.warranty_years)

        remaining_days = (expiry_date - today).days

        if remaining_days < 0:
            status = "Expired"
        elif remaining_days <= 30:
            status = "Expiring Soon"
        else:
            status = "Active"

        warranty_data.append({
            "product": item.product,
            "order_id": item.order.id,
            "order_date": order_date,
            "warranty_years": item.warranty_years,
            "expiry_date": expiry_date,
            "remaining_days": remaining_days,
            "status": status,
        })

    return render(request, "my_warranties.html", {
        "warranty_data": warranty_data
    })

def edit_review(request, review_id):
    user_id = request.session.get('user_id')
    review = get_object_or_404(Review, id=review_id)

    if not user_id or review.user.user_id != user_id:
        return redirect('product_detail', id=review.product.id)

    if request.method == "POST":
        review.rating = int(request.POST.get("rating"))
        review.comment = request.POST.get("comment")
        review.save()

    return redirect('product_detail', id=review.product.id)
def delete_review(request, review_id):
    user_id = request.session.get('user_id')
    review = get_object_or_404(Review, id=review_id)

    if user_id and review.user.user_id == user_id:
        product_id = review.product.id
        review.delete()
        return redirect('product_detail', id=product_id)

    return redirect('home')

from django.shortcuts import render, redirect
from django.db.models import Q
from .models import Product, Category

from django.contrib import messages
from django.db.models import Q
from .models import Product, Category

def search(request):
    query = request.GET.get("q")

    if not query:
        return redirect("home")

    # Search product
    product = Product.objects.filter(
        Q(name__icontains=query)
    ).first()

    if product:
        return redirect("product_detail", id=product.id)

    # Search category
    category = Category.objects.filter(
        Q(name__icontains=query)
    ).first()

    if category:
        return redirect("product_list", category.category_id)

    # If nothing found → show message and stay on home
    messages.error(request, f'No product or category found for "{query}"')
    return redirect("home")



def invoice_view(request, order_id):
    order = Order.objects.get(id=order_id)
    order_items = OrderItem.objects.filter(order=order)

    return render(request, "invoice.html", {
        "order": order,
        "order_items": order_items
    })

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Allow cancel only if status is Pending or Accepted
    if order.status in ["Pending", "Accepted"]:

        # Restore stock
        for item in order.items.all():
            product = item.product
            product.stock += item.quantity
            product.save()

        order.status = "Cancelled"
        order.save()

        messages.success(request, "Your order has been cancelled successfully.")

    return redirect('order_detail', order_id=order.id)





#############################################################################
#####################              ADMIN              #######################
#############################################################################

def admin_login(request):

    # If already logged in
    if request.session.get(settings.ADMIN_SESSION_KEY):
        return redirect("admin_dashboard")

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        if (
            email == settings.ADMIN_EMAIL and
            password == settings.ADMIN_PASSWORD
        ):
            request.session[settings.ADMIN_SESSION_KEY] = True
            request.session["admin_email"] = email

            return redirect("admin_dashboard")
        else:
            messages.error(request, "Invalid admin credentials")

    return render(request, "admin/login.html")


def admin_logout(request):
    request.session.pop(settings.ADMIN_SESSION_KEY, None)
    request.session.pop("admin_email", None)
    return redirect("admin_login")

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get(settings.ADMIN_SESSION_KEY):
            return redirect("admin_login")
        return view_func(request, *args, **kwargs)
    return wrapper

from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

@admin_required
def admin_dashboard(request):

    total_customers = User.objects.count()
    total_products = Product.objects.count()
    total_orders = Order.objects.count()

    total_revenue = Order.objects.filter(
        status="Completed"
    ).aggregate(total=Sum("total"))["total"] or 0

    # 📅 Revenue This Month
    today = timezone.now()
    first_day = today.replace(day=1)

    monthly_revenue = Order.objects.filter(
        status="Completed",
        created_at__gte=first_day
    ).aggregate(total=Sum("total"))["total"] or 0

    # 🏆 Best Selling Products
    best_selling = (
        OrderItem.objects
        .values("product__name")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:5]
    )

    # ⚡ Best Performance Products (by revenue)
    best_performing = (
        OrderItem.objects
        .values("product__name")
        .annotate(total_revenue=Sum("price"))
        .order_by("-total_revenue")[:5]
    )

    # 🚨 Low Stock Products
    low_stock = Product.objects.filter(stock__lt=10).order_by("stock")[:5]

    # 📦 Recent Orders
    recent_orders = Order.objects.order_by("-created_at")[:5]

    context = {
        "total_customers": total_customers,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "monthly_revenue": monthly_revenue,
        "best_selling": best_selling,
        "best_performing": best_performing,
        "low_stock": low_stock,
        "recent_orders": recent_orders,
    }

    return render(request, "admin/dashboard.html", context)
#check a file type
import os
from django.contrib import messages

def is_valid_image(file):
    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    ext = os.path.splitext(file.name)[1].lower()

    if ext not in valid_extensions:
        return False

    if not file.content_type.startswith("image"):
        return False

    return True

#magae users



def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get(settings.ADMIN_SESSION_KEY):
            return redirect("admin_login")
        return view_func(request, *args, **kwargs)
    return wrapper


@admin_required
def manage_users(request):

    query = request.GET.get("q", "")

    users = User.objects.all().order_by("-user_id")

    if query:
        users = users.filter(
            Q(first_name__icontains=query) |
            Q(email_id__icontains=query) |
            Q(contact_no__icontains=query)
        )

    paginator = Paginator(users, 8)  # 8 per page
    page_number = request.GET.get("page")
    users_page = paginator.get_page(page_number)

    context = {
        "users": users_page,
        "query": query
    }

    return render(request, "admin/manage_users.html", context)


@admin_required
def delete_user(request, user_id):
    user = User.objects.get(user_id=user_id)
    user.delete()
    return redirect("manage_users")


#manage reviews
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Review


@admin_required
def manage_reviews(request):

    query = request.GET.get("q", "")

    reviews = Review.objects.select_related("product", "user").order_by("-created_at")

    if query:
        reviews = reviews.filter(
            Q(product__name__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(comment__icontains=query)
        )

    paginator = Paginator(reviews, 10)
    page_number = request.GET.get("page")
    reviews_page = paginator.get_page(page_number)

    context = {
        "reviews": reviews_page,
        "query": query
    }

    return render(request, "admin/manage_reviews.html", context)

#manage category
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect
from django.utils.text import slugify
from .models import Category


@admin_required
def manage_categories(request):

    query = request.GET.get("q", "")
    categories = Category.objects.all().order_by("-category_id")

    if query:
        categories = categories.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    # Handle Add / Edit / Delete
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            name = request.POST.get("name")
            description = request.POST.get("description")
            image = request.FILES.get("image")

            if not name or not description or not image:
                messages.error(request, "All fields are required.")
                return redirect("manage_categories")

            # 🔐 Validate image
            if not is_valid_image(image):
                messages.error(request, "Only JPG, JPEG, PNG, WEBP images are allowed.")
                return redirect("manage_categories")

            Category.objects.create(
                name=name,
                description=description,
                image=image
            )

            messages.success(request, "Category added successfully.")
            return redirect("manage_categories")

        elif action == "edit":
            category_id = request.POST.get("category_id")
            category = Category.objects.get(category_id=category_id)

            name = request.POST.get("name")
            description = request.POST.get("description")

            if not name or not description:
                messages.error(request, "Name and Description are required.")
                return redirect("manage_categories")

            category.name = name
            category.description = description

            new_image = request.FILES.get("image")

            if new_image:
                if not is_valid_image(new_image):
                    messages.error(request, "Only JPG, JPEG, PNG, WEBP images are allowed.")
                    return redirect("manage_categories")

                category.image = new_image

            category.slug = slugify(category.name)
            category.save()

            messages.success(request, "Category updated successfully.")
            return redirect("manage_categories")

        elif action == "delete":
            category_id = request.POST.get("category_id")
            Category.objects.get(category_id=category_id).delete()
            return redirect("manage_categories")

    paginator = Paginator(categories, 8)
    page_number = request.GET.get("page")
    categories_page = paginator.get_page(page_number)

    context = {
        "categories": categories_page,
        "query": query
    }

    return render(request, "admin/manage_categories.html", context)

#manage feature 
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from .models import Feature


@admin_required
def manage_features(request):

    query = request.GET.get("q", "")
    features = Feature.objects.all().order_by("-id")

    if query:
        features = features.filter(name__icontains=query)

    # Handle CRUD
    if request.method == "POST":
        action = request.POST.get("action")

        # ADD
        if action == "add":
            name = request.POST.get("name")

            if not name:
                messages.error(request, "Feature name is required.")
                return redirect("manage_features")

            if Feature.objects.filter(name__iexact=name).exists():
                messages.error(request, "Feature already exists.")
                return redirect("manage_features")

            Feature.objects.create(name=name)
            messages.success(request, "Feature added successfully.")
            return redirect("manage_features")

        # EDIT
        elif action == "edit":
            feature_id = request.POST.get("feature_id")
            name = request.POST.get("name")

            if not name:
                messages.error(request, "Feature name is required.")
                return redirect("manage_features")

            feature = Feature.objects.get(id=feature_id)
            feature.name = name
            feature.save()

            messages.success(request, "Feature updated successfully.")
            return redirect("manage_features")

        # DELETE
        elif action == "delete":
            feature_id = request.POST.get("feature_id")
            Feature.objects.get(id=feature_id).delete()

            messages.success(request, "Feature deleted successfully.")
            return redirect("manage_features")

    paginator = Paginator(features, 10)
    page_number = request.GET.get("page")
    features_page = paginator.get_page(page_number)

    context = {
        "features": features_page,
        "query": query
    }

    return render(request, "admin/manage_features.html", context)

#manage product
from .models import Product, Category, Feature, ProductImage

@admin_required
def manage_products(request):

    query = request.GET.get("q", "")
    product_list = Product.objects.select_related("category").prefetch_related("features").order_by("-id")

    if query:
        product_list = product_list.filter(name__icontains=query)

    categories = Category.objects.all()
    features = Feature.objects.all()

    if request.method == "POST":
        action = request.POST.get("action")

        name = request.POST.get("name")
        description = request.POST.get("description")
        category_id = request.POST.get("category")
        price = request.POST.get("price")
        stock = request.POST.get("stock")
        warranty = request.POST.get("warranty_years")
        feature_ids = request.POST.getlist("features")

        # ADD PRODUCT
        if action == "add":

            image = request.FILES.get("image")

            if not all([name, description, category_id, price, stock, image]):
                messages.error(request, "All required fields must be filled.")
                return redirect("manage_products")
            if not is_valid_image(image):
                messages.error(request, "Main image must be JPG, PNG, WEBP under 3MB.")
                return redirect("manage_products")
            product = Product.objects.create(
                name=name,
                description=description,
                category_id=category_id,
                price=price,
                stock=stock,
                warranty_years=warranty if warranty else None,
                image=image
            )

            product.features.set(feature_ids)

            messages.success(request, "Product added successfully.")
            return redirect("manage_products")

        # EDIT PRODUCT
        elif action == "edit":

            product_id = request.POST.get("product_id")
            product = Product.objects.get(id=product_id)

            product.name = name
            product.description = description
            product.category_id = category_id
            product.price = price
            product.stock = stock
            product.warranty_years = warranty if warranty else None

            # Only update main image if new one uploaded
            new_image = request.FILES.get("image")
            if new_image:
                if not is_valid_image(new_image):
                    messages.error(request, "Main image must be JPG, PNG, WEBP under 3MB.")
                    return redirect("manage_products")
            product.save()
            product.features.set(feature_ids)

            messages.success(request, "Product updated successfully.")
            return redirect("manage_products")

        # DELETE
        elif action == "delete":
            Product.objects.get(id=request.POST.get("product_id")).delete()
            messages.success(request, "Product deleted.")
            return redirect("manage_products")

    paginator = Paginator(product_list, 8)
    page_number = request.GET.get("page")
    products = paginator.get_page(page_number)

    return render(request, "admin/manage_products.html", {
        "products": products,
        "categories": categories,
        "features": features,
        "query": query
    })

#manage stock
from django.core.paginator import Paginator

@admin_required
def manage_stock(request):

    product_list = Product.objects.all().order_by("name")

    # 🔢 Add Pagination
    paginator = Paginator(product_list, 8)  # 8 per page
    page_number = request.GET.get("page")
    products = paginator.get_page(page_number)

    if request.method == "POST":
        product_id = request.POST.get("product_id")
        stock = request.POST.get("stock")
        try:
            stock = int(stock)
        except (TypeError, ValueError):
            messages.error(request, "Invalid stock quantity.")
            return redirect("manage_stock")

        # Validation
        if stock < 0:
            messages.error(request, "Stock cannot be negative.")
            return redirect("manage_stock")

        if stock > 200:
            messages.error(request, "Maximum allowed stock is 200.")
            return redirect("manage_stock")
        product = Product.objects.get(id=product_id)
        product.stock = stock
        product.save()

        messages.success(request, "Stock updated.")
        return redirect("manage_stock")

    return render(request, "admin/manage_stock.html", {
        "products": products
    })


#manage product imges
@admin_required
def manage_product_images(request, product_id):

    product = Product.objects.get(id=product_id)
    images = product.images.all()

    if request.method == "POST":
        action = request.POST.get("action")

        # ADD IMAGE
        if action == "add":
            new_images = request.FILES.getlist("images")

            if not new_images:
                messages.error(request, "Please select at least one image.")
                return redirect("manage_product_images", product_id=product.id)

            for img in new_images:
                if not is_valid_image(img):
                    messages.error(request, "Only JPG, JPEG, PNG, WEBP under 3MB allowed.")
                    return redirect("manage_product_images", product_id=product.id)

                ProductImage.objects.create(product=product, image=img)

            messages.success(request, "Images added successfully.")
            return redirect("manage_product_images", product_id=product.id)

        # SET PRIMARY
        elif action == "set_primary":
            image_id = request.POST.get("image_id")

            try:
                primary_image = ProductImage.objects.get(id=image_id, product=product)
            except ProductImage.DoesNotExist:
                messages.error(request, "Invalid image.")
                return redirect("manage_product_images", product_id=product.id)

            ProductImage.objects.filter(product=product).update(is_primary=False)

            primary_image.is_primary = True
            primary_image.save()

            product.image = primary_image.image
            product.save()

            messages.success(request, "Primary image updated.")
            return redirect("manage_product_images", product_id=product.id)

        # DELETE IMAGE
        elif action == "delete":
            image_id = request.POST.get("image_id")

            try:
                image = ProductImage.objects.get(id=image_id, product=product)
            except ProductImage.DoesNotExist:
                messages.error(request, "Invalid image.")
                return redirect("manage_product_images", product_id=product.id)

            image.delete()

            messages.success(request, "Image deleted.")
            return redirect("manage_product_images", product_id=product.id)

    return render(request, "admin/manage_product_images.html", {
        "product": product,
        "images": images
    })

#manage order
from .models import Order
from django.core.paginator import Paginator
from django.contrib import messages

@admin_required
def manage_orders(request):
    query = request.GET.get("q", "")

    order_list = Order.objects.select_related("user").prefetch_related("items").order_by("-id")

    if query:
        order_list = order_list.filter(
            Q(full_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )

        if query.isdigit():
            order_list = order_list | Order.objects.filter(id=int(query))        
    if request.method == "POST":
        order_id = request.POST.get("order_id")
        new_status = request.POST.get("status")

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            messages.error(request, "Invalid order.")
            return redirect("manage_orders")

        # 🔒 Prevent Cancelled selection
        if new_status == "Cancelled":
            messages.error(request, "Admin cannot set order to Cancelled.")
            return redirect("manage_orders")

        # Only update if valid status
        valid_statuses = ["Pending", "Accepted", "Ready", "Completed"]

        if new_status not in valid_statuses:
            messages.error(request, "Invalid status.")
            return redirect("manage_orders")

        order.status = new_status
        order.save()  # your save() handles email

        messages.success(request, "Order status updated successfully.")
        return redirect("manage_orders")

    paginator = Paginator(order_list, 8)
    page_number = request.GET.get("page")
    orders = paginator.get_page(page_number)

    return render(request, "admin/manage_orders.html", {
        "orders": orders,
        "query": query
    })

#manage order details
from django.http import JsonResponse

@admin_required
def get_order_details(request, order_id):

    try:
        order = Order.objects.prefetch_related("items__product").get(id=order_id)
    except Order.DoesNotExist:
        return JsonResponse({"error": "Invalid order"}, status=400)

    items_data = []

    for item in order.items.all():

        warranty_expiry = None
        warranty_status = "No Warranty"

        if item.warranty_years:
            warranty_expiry = order.created_at + timedelta(days=365 * item.warranty_years)
            warranty_status = "Expired" if warranty_expiry < timezone.now() else "Active"

        items_data.append({
            "product": item.product.name,
            "image": item.product.image.url if item.product.image else "",
            "quantity": item.quantity,
            "price": float(item.price),
            "subtotal": float(item.subtotal()),
            "warranty_years": item.warranty_years,
            "warranty_expiry": warranty_expiry.strftime("%Y-%m-%d") if warranty_expiry else None,
            "warranty_status": warranty_status
        })

    return JsonResponse({
        "order_id": order.id,
        "customer": order.full_name,
        "total": float(order.total),
        "items": items_data
    })

#manage revenue
from django.db.models import Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q

@admin_required
def revenue_dashboard(request):

    today = timezone.now().date()
    first_day_of_month = today.replace(day=1)

    completed_orders = Order.objects.filter(status="Completed")

    # ===== Basic Stats =====
    total_revenue = completed_orders.aggregate(total=Sum("total"))["total"] or 0
    today_revenue = completed_orders.filter(
        created_at__date=today
    ).aggregate(total=Sum("total"))["total"] or 0

    monthly_revenue = completed_orders.filter(
        created_at__date__gte=first_day_of_month
    ).aggregate(total=Sum("total"))["total"] or 0

    # ===== Last 7 Days Revenue =====
    last_7_days = today - timedelta(days=6)

    daily_revenue_qs = (
        completed_orders
        .filter(created_at__date__gte=last_7_days)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Sum("total"))
        .order_by("day")
    )

    daily_labels = []
    daily_data = []

    for i in range(7):
        day = last_7_days + timedelta(days=i)
        daily_labels.append(day.strftime("%d %b"))

        day_total = next(
            (item["total"] for item in daily_revenue_qs if item["day"] == day),
            0
        )
        daily_data.append(float(day_total or 0))

    # ===== Monthly Revenue =====
    monthly_revenue_qs = (
        completed_orders
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("total"))
        .order_by("month")
    )

    monthly_labels = []
    monthly_data = []

    for item in monthly_revenue_qs:
        monthly_labels.append(item["month"].strftime("%b %Y"))
        monthly_data.append(float(item["total"]))

    context = {
        "total_revenue": total_revenue,
        "today_revenue": today_revenue,
        "monthly_revenue": monthly_revenue,

        "daily_labels": daily_labels,
        "daily_data": daily_data,

        "monthly_labels": monthly_labels,
        "monthly_data": monthly_data,
    }

    return render(request, "admin/revenue_dashboard.html", context)

#reports 
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum

from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

@admin_required
def admin_reports(request):

    report_type = request.GET.get("type")
    range_filter = request.GET.get("range")

    data = []
    labels = []
    values = []

    today = timezone.now()
    start_date = None

    # ===== Date Range Logic =====
    if range_filter == "1m":
        start_date = today - timedelta(days=30)
    elif range_filter == "3m":
        start_date = today - timedelta(days=90)
    elif range_filter == "6m":
        start_date = today - timedelta(days=180)
    elif range_filter == "12m":
        start_date = today - timedelta(days=365)
    elif range_filter == "all":
        start_date = None

    if report_type:

        # ===== ORDERS =====
        if report_type == "orders":

            qs = Order.objects.all()
            if start_date:
                qs = qs.filter(created_at__gte=start_date)

            data = qs

            labels = ["Pending", "Accepted", "Ready", "Completed", "Cancelled"]
            values = [
                qs.filter(status="Pending").count(),
                qs.filter(status="Accepted").count(),
                qs.filter(status="Ready").count(),
                qs.filter(status="Completed").count(),
                qs.filter(status="Cancelled").count(),
            ]

        # ===== REVENUE =====
        elif report_type == "revenue":

            qs = Order.objects.filter(status="Completed")
            if start_date:
                qs = qs.filter(created_at__gte=start_date)

            total = qs.aggregate(total=Sum("total"))["total"] or 0

            data = qs
            labels = ["Revenue"]
            values = [float(total)]

        # ===== PRODUCTS =====
        elif report_type == "products":

            qs = Product.objects.all()
            if start_date:
                qs = qs.filter(created_at__gte=start_date)

            data = qs
            labels = ["Products Added"]
            values = [qs.count()]

        # ===== CUSTOMERS =====
        elif report_type == "customers":

            qs = User.objects.all()
            data = qs
            labels = ["Total Customers"]
            values = [qs.count()]

    return render(request, "admin/admin_reports.html", {
        "report_type": report_type,
        "range_filter": range_filter,
        "data": data,
        "labels": labels,
        "values": values,
    })
#download
@admin_required
def download_report(request):

    report_type = request.GET.get("type")
    range_filter = request.GET.get("range")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=report.csv"

    writer = csv.writer(response)

    if report_type == "orders":
        writer.writerow(["Order ID", "Customer", "Total", "Status", "Date"])
        for order in Order.objects.all():
            writer.writerow([
                order.id,
                order.full_name,
                order.total,
                order.status,
                order.created_at
            ])

    elif report_type == "revenue":
        writer.writerow(["Order ID", "Total", "Date"])
        for order in Order.objects.filter(status="Completed"):
            writer.writerow([order.id, order.total, order.created_at])

    return response

#download pdf
@admin_required
def download_report_pdf(request):

    report_type = request.GET.get("type")
    range_filter = request.GET.get("range")

    today = timezone.now()
    start_date = None

    if range_filter == "1m":
        start_date = today - timedelta(days=30)
    elif range_filter == "3m":
        start_date = today - timedelta(days=90)
    elif range_filter == "6m":
        start_date = today - timedelta(days=180)
    elif range_filter == "12m":
        start_date = today - timedelta(days=365)
    elif range_filter == "all":
        start_date = None

    headers = []
    rows = []

    # ===== ORDERS =====
    if report_type == "orders":

        qs = Order.objects.all()
        if start_date:
            qs = qs.filter(created_at__gte=start_date)

        headers = ["Order ID", "Customer", "Total", "Status"]

        for order in qs:
            rows.append([
                str(order.id),
                order.full_name,
                f"Rs. {order.total}",
                order.status
            ])

        return generate_pdf("Orders Report", headers, rows)

    # ===== REVENUE =====
    elif report_type == "revenue":

        qs = Order.objects.filter(status="Completed")
        if start_date:
            qs = qs.filter(created_at__gte=start_date)

        headers = ["Order ID", "Amount"]

        for order in qs:
            rows.append([
                str(order.id),
                f"Rs. {order.total}"
            ])

        return generate_pdf("Revenue Report", headers, rows)

    # ===== PRODUCTS =====
    elif report_type == "products":

        qs = Product.objects.all()
        if start_date:
            qs = qs.filter(created_at__gte=start_date)

        headers = ["Product", "Price", "Stock"]

        for product in qs:
            rows.append([
                product.name,
                f"Rs. {product.price}",
                str(product.stock)
            ])

        return generate_pdf("Products Report", headers, rows)

    # ===== CUSTOMERS =====
    elif report_type == "customers":

        qs = User.objects.all()

        headers = ["Customer Name", "Email"]

        for user in qs:
            rows.append([
                user.first_name,
                user.email_id
            ])

        return generate_pdf("Customers Report", headers, rows)