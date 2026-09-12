from django.shortcuts import render,redirect,reverse, get_object_or_404
from . import forms,models
from django.http import HttpResponseRedirect,HttpResponse
from django.core.mail import send_mail
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg, Count, Sum
import base64
import io
import qrcode
import secrets
from datetime import timedelta
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError

def home_view(request):
    products=models.Product.objects.all()
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0
    wished_ids=set()
    if request.user.is_authenticated:
        customer=models.Customer.objects.filter(user=request.user).first()
        if customer:
            wished_ids=set(models.Wishlist.objects.filter(customer=customer).values_list('product_id',flat=True))
        return HttpResponseRedirect('afterlogin')
    return render(request,'ecom/index.html',{'products':products,'product_count_in_cart':product_count_in_cart,'wished_ids':wished_ids})


#for showing login button for admin(by sumit)
def adminclick_view(request):
    if request.user.is_authenticated:
        return redirect('afterlogin')
    return redirect('adminlogin')

def customer_login_view(request):
    if request.user.is_authenticated:
        return redirect('afterlogin')
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')
        user = models.User.objects.filter(email__iexact=identifier).first() if identifier else None
        username = user.username if user else identifier
        user = authenticate(request, username=username, password=password) if identifier and password else None
        if user is not None and user.is_active and is_customer(user):
            login(request, user)
            return redirect('customer-home')
        messages.error(request, 'Customer username/email or password is incorrect.')
    return render(request, 'ecom/customerlogin.html')

def admin_login_view(request):
    if request.user.is_authenticated:
        return redirect('afterlogin')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password) if username and password else None
        if user is not None and user.is_active and is_admin(user):
            login(request, user)
            return redirect('admin-dashboard')
        messages.error(request, 'Admin username or password is incorrect.')
    return render(request, 'ecom/adminlogin.html')

def unified_login_view(request):
    return customer_login_view(request)


def customer_signup_view(request):
    userForm=forms.CustomerUserForm()
    customerForm=forms.CustomerForm()
    mydict={'userForm':userForm,'customerForm':customerForm}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST)
        customerForm=forms.CustomerForm(request.POST)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save(commit=False)
            user.set_password(userForm.cleaned_data['password'])
            user.save()
            customer=customerForm.save(commit=False)
            customer.user=user
            customer.save()
            my_customer_group = Group.objects.get_or_create(name='CUSTOMER')
            my_customer_group[0].user_set.add(user)
            messages.success(request, 'Account created successfully. Please sign in.')
            return redirect('customerlogin')
    return render(request,'ecom/customersignup.html',context=mydict)

def customer_password_reset_request_view(request):
    if request.user.is_authenticated:
        return redirect('afterlogin')
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        if not identifier:
            messages.error(request, 'Please enter your username or registered email address.')
            return render(request, 'ecom/forgot_password.html')

        user = models.User.objects.filter(email__iexact=identifier).first()
        if user is None:
            user = models.User.objects.filter(username__iexact=identifier).first()

        if not user or not user.is_active or not is_customer(user):
            messages.error(request, 'We could not find an active customer account with those details.')
            return render(request, 'ecom/forgot_password.html')
        if not user.email:
            messages.error(request, 'This account has no email address saved. Please ask the administrator to add your email in Customer Management, then try again.')
            return render(request, 'ecom/forgot_password.html')

        code = f"{secrets.randbelow(1000000):06d}"
        models.PasswordResetCode.objects.filter(email__iexact=user.email, used=False).update(used=True)
        reset = models.PasswordResetCode.objects.create(
            email=user.email, code=code, expires_at=timezone.now()+timedelta(minutes=10)
        )
        subject='Curious Cart password reset code'
        message=(
            f'Hello {user.first_name or user.username},\n\n'
            f'Your Curious Cart password reset verification code is: {code}\n\n'
            'This code expires in 10 minutes and can be used only once.\n\n'
            'If you did not request this, you can safely ignore this email.\n\n'
            'Curious Cart'
        )
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
        except Exception as exc:
            reset.delete()
            messages.error(request, 'The verification email could not be sent. Check the Gmail SMTP/App Password settings in the project .env file and try again.')
            return render(request, 'ecom/forgot_password.html')

        request.session['reset_email'] = user.email
        messages.success(request, f'A 6-digit verification code was sent to {user.email}. Check Inbox and Spam/Junk.')
        return redirect('verify-reset-code')
    return render(request, 'ecom/forgot_password.html')


def customer_password_reset_verify_view(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('forgot-password')
    if request.method == 'POST':
        code = request.POST.get('code','').strip()
        password1 = request.POST.get('password1','')
        password2 = request.POST.get('password2','')
        reset = models.PasswordResetCode.objects.filter(email__iexact=email, code=code, used=False).order_by('-created_at').first()
        if not reset or reset.expires_at < timezone.now():
            messages.error(request, 'Invalid or expired verification code. Please request a new code.')
        elif len(password1) < 8:
            messages.error(request, 'New password must contain at least 8 characters.')
        elif password1 != password2:
            messages.error(request, 'The new passwords do not match.')
        else:
            from django.contrib.auth.models import User
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if not user:
                messages.error(request, 'Account not found.')
            else:
                user.set_password(password1)
                user.save(update_fields=['password'])
                reset.used=True
                reset.save(update_fields=['used'])
                request.session.pop('reset_email', None)
                messages.success(request, 'Password reset successfully. You can now sign in with your new password.')
                return redirect('customerlogin')
    return render(request, 'ecom/reset_password.html', {'email': email})


#-----------for checking user iscustomer
def is_customer(user):
    return user.groups.filter(name='CUSTOMER').exists()


def is_admin(user):
    return user.is_staff or user.is_superuser



#---------AFTER ENTERING CREDENTIALS WE CHECK WHETHER USERNAME AND PASSWORD IS OF ADMIN,CUSTOMER
def afterlogin_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if is_customer(request.user):
        return redirect('customer-home')
    if request.user.is_staff or request.user.is_superuser:
        return redirect('admin-dashboard')
    logout(request)
    messages.error(request, 'This account does not have access to Curious Cart.')
    return redirect('login')

#---------------------------------------------------------------------------------
#------------------------ ADMIN RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
@login_required(login_url='adminlogin')
@user_passes_test(is_admin, login_url='adminlogin')
def admin_change_password_view(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Admin password changed successfully. Please use the new password next time you sign in.')
        return redirect('admin-dashboard')
    return render(request, 'ecom/admin_change_password.html', {'form': form})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def admin_edit_profile_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        if not first_name:
            messages.error(request, 'Admin name is required.')
        else:
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.save(update_fields=['first_name', 'last_name'])
            messages.success(request, 'Admin name updated successfully.')
            return redirect('admin-dashboard')
    return render(request, 'ecom/admin_edit_profile.html', {'admin_user': request.user})

def admin_dashboard_view(request):
    # for cards on dashboard
    customercount=models.Customer.objects.all().count()
    productcount=models.Product.objects.all().count()
    ordercount=models.Orders.objects.all().count()
    revenue=sum((o.product.price-o.discount) for o in models.Orders.objects.select_related('product').all() if o.product)
    deliveredcount=models.Orders.objects.filter(status='Delivered').count()
    top_products=models.Product.objects.annotate(order_total=Count('orders')).order_by('-order_total')[:5]

    # for recent order tables
    orders=models.Orders.objects.all()
    ordered_products=[]
    ordered_bys=[]
    for order in orders:
        ordered_product=models.Product.objects.all().filter(id=order.product.id)
        ordered_by=models.Customer.objects.all().filter(id = order.customer.id)
        ordered_products.append(ordered_product)
        ordered_bys.append(ordered_by)

    mydict={
    'customercount':customercount,
    'productcount':productcount,
    'ordercount':ordercount,
    'revenue':revenue, 'deliveredcount':deliveredcount, 'top_products':top_products,
    'data':zip(ordered_products,ordered_bys,orders),
    }
    return render(request,'ecom/admin_dashboard.html',context=mydict)


# admin view customer table
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def view_customer_view(request):
    customers=models.Customer.objects.all()
    return render(request,'ecom/view_customer.html',{'customers':customers})

# admin delete customer
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def delete_customer_view(request,pk):
    customer=models.Customer.objects.get(id=pk)
    user=models.User.objects.get(id=customer.user_id)
    user.delete()
    customer.delete()
    return redirect('view-customer')


@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def update_customer_view(request,pk):
    customer=models.Customer.objects.get(id=pk)
    user=models.User.objects.get(id=customer.user_id)
    userForm=forms.CustomerUserForm(instance=user)
    customerForm=forms.CustomerForm(instance=customer)
    mydict={'userForm':userForm,'customerForm':customerForm}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST,instance=user)
        customerForm=forms.CustomerForm(request.POST,instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save(commit=False)
            new_password=userForm.cleaned_data.get('password')
            if new_password:
                user.set_password(new_password)
            user.save()
            customerForm.save()
            return redirect('view-customer')
    return render(request,'ecom/admin_update_customer.html',context=mydict)

# admin view the product
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def admin_products_view(request):
    products=models.Product.objects.all()
    return render(request,'ecom/admin_products.html',{'products':products})


# admin add product by clicking on floating button
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def admin_add_product_view(request):
    productForm=forms.ProductForm()
    if request.method=='POST':
        productForm=forms.ProductForm(request.POST, request.FILES)
        if productForm.is_valid():
            productForm.save()
        return HttpResponseRedirect('admin-products')
    return render(request,'ecom/admin_add_products.html',{'productForm':productForm})


@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def delete_product_view(request,pk):
    product=models.Product.objects.get(id=pk)
    product.delete()
    return redirect('admin-products')


@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def update_product_view(request,pk):
    product=models.Product.objects.get(id=pk)
    productForm=forms.ProductForm(instance=product)
    if request.method=='POST':
        productForm=forms.ProductForm(request.POST,request.FILES,instance=product)
        if productForm.is_valid():
            productForm.save()
            return redirect('admin-products')
    return render(request,'ecom/admin_update_product.html',{'productForm':productForm})


@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def admin_view_booking_view(request):
    orders=models.Orders.objects.all()
    ordered_products=[]
    ordered_bys=[]
    for order in orders:
        ordered_product=models.Product.objects.all().filter(id=order.product.id)
        ordered_by=models.Customer.objects.all().filter(id = order.customer.id)
        ordered_products.append(ordered_product)
        ordered_bys.append(ordered_by)
    return render(request,'ecom/admin_view_booking.html',{'data':zip(ordered_products,ordered_bys,orders)})


@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def delete_order_view(request,pk):
    order=models.Orders.objects.get(id=pk)
    order.delete()
    return redirect('admin-view-booking')

# for changing status of order (pending,delivered...)
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def update_order_view(request,pk):
    order=models.Orders.objects.get(id=pk)
    orderForm=forms.OrderForm(instance=order)
    if request.method=='POST':
        orderForm=forms.OrderForm(request.POST,instance=order)
        if orderForm.is_valid():
            orderForm.save()
            return redirect('admin-view-booking')
    return render(request,'ecom/update_order.html',{'orderForm':orderForm})



@login_required(login_url='adminlogin')
@user_passes_test(is_admin, login_url='adminlogin')
def admin_reviews_view(request):
    reviews = (models.Review.objects
               .select_related('product', 'customer__user')
               .order_by('-created_at'))
    return render(request, 'ecom/admin_reviews.html', {'reviews': reviews})


#---------------------------------------------------------------------------------
#------------------------ PUBLIC CUSTOMER RELATED VIEWS START ---------------------
#---------------------------------------------------------------------------------
def search_view(request):
    query=request.GET.get('query','').strip()
    sort=request.GET.get('sort','').strip()
    products=models.Product.objects.all()
    if query:
        from django.db.models import Q
        products=products.filter(Q(name__icontains=query)|Q(description__icontains=query))
    if sort=='price_asc': products=products.order_by('price')
    elif sort=='price_desc': products=products.order_by('-price')
    elif sort=='newest': products=products.order_by('-created_at')
    wished_ids=set();
    if request.user.is_authenticated:
        customer=models.Customer.objects.filter(user=request.user).first()
        if customer: wished_ids=set(models.Wishlist.objects.filter(customer=customer).values_list('product_id',flat=True))
    return render(request,'ecom/search.html',{'products':products.distinct(),'word':f'Results for “{query}”' if query else 'All products','selected_sort':sort,'product_count_in_cart':_cart_count(request),'wished_ids':wished_ids})


def add_to_cart_view(request,pk):
    products=models.Product.objects.all()

    #for cart counter, fetching products ids added by customer from cookies
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=1

    wished_ids=set()
    if request.user.is_authenticated:
        customer=models.Customer.objects.filter(user=request.user).first()
        if customer:
            wished_ids=set(models.Wishlist.objects.filter(customer=customer).values_list('product_id',flat=True))
    response = render(request, 'ecom/index.html',{'products':products,'product_count_in_cart':product_count_in_cart,'wished_ids':wished_ids})

    #adding product id to cookies
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids=="":
            product_ids=str(pk)
        else:
            product_ids=product_ids+"|"+str(pk)
        response.set_cookie('product_ids', product_ids)
    else:
        response.set_cookie('product_ids', pk)

    product=models.Product.objects.get(id=pk)
    messages.info(request, product.name + ' added to cart successfully!')

    return response



# for checkout of cart
def cart_view(request):
    products=_cart_products(request); total,discount,code=_discounted_total(request)
    return render(request,'ecom/cart.html',{'products':products,'total':total,'discount':discount,'grand_total':total-discount,'coupon_code':code,'product_count_in_cart':_cart_count(request)})


def remove_from_cart_view(request,pk):
    #for counter in cart
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0

    # removing product id from cookie
    total=0
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        product_id_in_cart=product_ids.split('|')
        product_id_in_cart=list(set(product_id_in_cart))
        product_id_in_cart.remove(str(pk))
        products=models.Product.objects.all().filter(id__in = product_id_in_cart)
        #for total price shown in cart after removing product
        for p in products:
            total=total+p.price

        #  for update coookie value after removing product id in cart
        value=""
        for i in range(len(product_id_in_cart)):
            if i==0:
                value=value+product_id_in_cart[0]
            else:
                value=value+"|"+product_id_in_cart[i]
        response = render(request, 'ecom/cart.html',{'products':products,'total':total,'product_count_in_cart':product_count_in_cart})
        if value=="":
            response.delete_cookie('product_ids')
        response.set_cookie('product_ids',value)
        return response


def send_feedback_view(request):
    feedbackForm=forms.FeedbackForm()
    if request.method == 'POST':
        feedbackForm = forms.FeedbackForm(request.POST)
        if feedbackForm.is_valid():
            feedbackForm.save()
            return render(request, 'ecom/feedback_sent.html')
    return render(request, 'ecom/send_feedback.html', {'feedbackForm':feedbackForm})


#---------------------------------------------------------------------------------
#------------------------ CUSTOMER RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
@login_required(login_url='login')
@user_passes_test(is_customer)
def customer_home_view(request):
    customer=models.Customer.objects.filter(user=request.user).first()
    ordered_ids=list(models.Orders.objects.filter(customer=customer).values_list('product_id',flat=True)) if customer else []
    wished_ids=list(models.Wishlist.objects.filter(customer=customer).values_list('product_id',flat=True)) if customer else []
    products=models.Product.objects.exclude(id__in=ordered_ids).order_by('-created_at')[:12]
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0
    return render(request,'ecom/customer_home.html',{'products':products,'product_count_in_cart':product_count_in_cart,'wished_ids':set(wished_ids)})



# shipment address before placing order
@login_required(login_url='login')
def customer_address_view(request):
    # this is for checking whether product is present in cart or not
    # if there is no product in cart we will not show address form
    product_in_cart=False
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids != "":
            product_in_cart=True
    #for counter in cart
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0

    addressForm = forms.AddressForm()
    if request.method == 'POST':
        addressForm = forms.AddressForm(request.POST)
        if addressForm.is_valid():
            # here we are taking address, email, mobile at time of order placement
            # we are not taking it from customer account table because
            # these thing can be changes
            email = addressForm.cleaned_data['Email']
            mobile=addressForm.cleaned_data['Mobile']
            address = addressForm.cleaned_data['Address']
            #for showing total price on payment page.....accessing id from cookies then fetching  price of product from db
            total=0
            if 'product_ids' in request.COOKIES:
                product_ids = request.COOKIES['product_ids']
                if product_ids != "":
                    product_id_in_cart=product_ids.split('|')
                    products=models.Product.objects.all().filter(id__in = product_id_in_cart)
                    for p in products:
                        total=total+p.price

            response = redirect('payment')
            response.set_cookie('email',email)
            response.set_cookie('mobile',mobile)
            response.set_cookie('address',address)
            return response
    return render(request,'ecom/customer_address.html',{'addressForm':addressForm,'product_in_cart':product_in_cart,'product_count_in_cart':product_count_in_cart})




@login_required(login_url='login')
def payment_view(request):
    """Display the checkout payment options and a UPI QR code.

    This project intentionally uses a demo payment flow. Selecting UPI creates
    a standard UPI deep-link QR code from the configured demo UPI ID. The app
    does not verify transactions with a payment gateway.
    """
    product_ids = request.COOKIES.get('product_ids', '')
    if not product_ids:
        messages.info(request, 'Your cart is empty. Please add a product first.')
        return redirect('customer-home')

    product_id_in_cart = [pid for pid in product_ids.split('|') if pid]
    products = models.Product.objects.filter(id__in=product_id_in_cart)
    subtotal = sum(product.price for product in products)
    coupon = request.session.get('coupon_code','')
    discount = 0
    if coupon:
        c=models.Coupon.objects.filter(code__iexact=coupon,active=True).first()
        if c and (not c.expires_at or c.expires_at >= timezone.now()): discount=round(subtotal*c.percent/100)
        else: request.session.pop('coupon_code',None); coupon=''
    total = subtotal-discount
    payment_method = request.POST.get('payment_method', 'upi') if request.method == 'POST' else 'upi'

    upi_id = getattr(settings, 'UPI_ID', 'curiouscart@upi')
    upi_name = getattr(settings, 'UPI_PAYEE_NAME', 'Curious Cart')
    upi_uri = f"upi://pay?pa={upi_id}&pn={upi_name}&am={total}&cu=INR"

    qr_data = None
    if payment_method == 'upi':
        qr = qrcode.QRCode(version=1, box_size=8, border=4)
        qr.add_data(upi_uri)
        qr.make(fit=True)
        image = qr.make_image()
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        qr_data = base64.b64encode(buffer.getvalue()).decode('ascii')

    if request.method == 'POST':
        if payment_method not in {'upi', 'card', 'cod'}:
            payment_method = 'upi'
        request.session['payment_completed'] = True
        request.session['payment_method'] = payment_method
        return redirect('payment-success')

    return render(request, 'ecom/payment.html', {
        'total': total,
        'subtotal': subtotal, 'discount': discount, 'coupon_code': coupon,
        'payment_method': payment_method,
        'upi_id': upi_id,
        'upi_uri': upi_uri,
        'qr_data': qr_data,
    })


# here we are just directing to this view...actually we have to check whther payment is successful or not
#then only this view should be accessed
@login_required(login_url='login')
def payment_success_view(request):
    if not request.session.pop('payment_completed', False):
        return redirect('payment')
    # Here we will place order | after successful payment
    # we will fetch customer  mobile, address, Email
    # we will fetch product id from cookies then respective details from db
    # then we will create order objects and store in db
    # after that we will delete cookies because after order placed...cart should be empty
    customer=models.Customer.objects.get(user_id=request.user.id)
    products=None
    email=None
    mobile=None
    address=None
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids != "":
            product_id_in_cart=product_ids.split('|')
            products=models.Product.objects.all().filter(id__in = product_id_in_cart)
            # Here we get products list that will be ordered by one customer at a time

    # these things can be change so accessing at the time of order...
    if 'email' in request.COOKIES:
        email=request.COOKIES['email']
    if 'mobile' in request.COOKIES:
        mobile=request.COOKIES['mobile']
    if 'address' in request.COOKIES:
        address=request.COOKIES['address']

    # here we are placing number of orders as much there is a products
    # suppose if we have 5 items in cart and we place order....so 5 rows will be created in orders table
    # there will be lot of redundant data in orders table...but its become more complicated if we normalize it
    payment_method = request.session.pop('payment_method', 'Online Payment')
    payment_labels = {'upi': 'UPI / QR Code', 'card': 'Debit / Credit Card', 'cod': 'Cash on Delivery'}
    payment_method_label = payment_labels.get(payment_method, 'Online Payment')
    for product in products:
        models.Orders.objects.get_or_create(customer=customer,product=product,status='Pending',email=email,mobile=mobile,address=address,payment_method=payment_method_label,coupon_code=request.session.get('coupon_code',''),discount=discount if 'discount' in locals() else 0)

    # after order placed cookies should be deleted
    response = render(request,'ecom/payment_success.html')
    response.delete_cookie('product_ids')
    response.delete_cookie('email')
    response.delete_cookie('mobile')
    response.delete_cookie('address')
    request.session.pop('coupon_code',None)
    return response




@login_required(login_url='login')
@user_passes_test(is_customer)
def my_order_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    orders=models.Orders.objects.all().filter(customer_id = customer)
    ordered_products=[]
    for order in orders:
        ordered_product=models.Product.objects.all().filter(id=order.product.id)
        ordered_products.append(ordered_product)

    return render(request,'ecom/my_order.html',{'data':zip(ordered_products,orders)})




#--------------for discharge patient bill (pdf) download and printing
import io
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse


def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return

@login_required(login_url='login')
@user_passes_test(is_customer)
def download_invoice_view(request,orderID,productID):
    order=models.Orders.objects.get(id=orderID)
    product=models.Product.objects.get(id=productID)
    mydict={
        'orderDate':order.order_date,
        'customerName':request.user,
        'customerEmail':order.email,
        'customerMobile':order.mobile,
        'shipmentAddress':order.address,
        'orderStatus':order.status,

        'productName':product.name,
        'productImage':product.product_image,
        'productPrice':product.price,
        'productDescription':product.description,


    }
    return render_to_pdf('ecom/download_invoice.html',mydict)






@login_required(login_url='login')
@user_passes_test(is_customer)
def my_profile_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    return render(request,'ecom/my_profile.html',{'customer':customer})


@login_required(login_url='login')
@user_passes_test(is_customer)
def edit_profile_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    user=models.User.objects.get(id=customer.user_id)
    userForm=forms.CustomerUserForm(instance=user)
    customerForm=forms.CustomerForm(instance=customer)
    mydict={'userForm':userForm,'customerForm':customerForm}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST,instance=user)
        customerForm=forms.CustomerForm(request.POST,instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            new_user=userForm.save(commit=False)
            # Keep the existing password when the password field is left blank.
            raw_password=userForm.cleaned_data.get('password')
            if raw_password:
                new_user.set_password(raw_password)
            else:
                new_user.password=user.password
            new_user.save()
            customerForm.save()
            messages.success(request,'Profile updated successfully.')
            return redirect('my-profile')
    return render(request,'ecom/edit_profile.html',context=mydict)



#---------------------------------------------------------------------------------
#------------------------ ABOUT US AND CONTACT US VIEWS START --------------------
#---------------------------------------------------------------------------------
def aboutus_view(request):
    return render(request,'ecom/aboutus.html')

def contactus_view(request):
    sub = forms.ContactusForm()
    if request.method == 'POST':
        sub = forms.ContactusForm(request.POST)
        if sub.is_valid():
            email = sub.cleaned_data['Email']
            name=sub.cleaned_data['Name']
            message = sub.cleaned_data['Message']
            send_mail(str(name)+' || '+str(email), message, settings.DEFAULT_FROM_EMAIL, settings.EMAIL_RECEIVING_USER, fail_silently=False)
            return render(request, 'ecom/contactussuccess.html')
    return render(request, 'ecom/contactus.html', {'form':sub})


# ---------------- Curious Cart modern features ----------------
def _cart_ids(request):
    raw=request.COOKIES.get('product_ids','')
    return [x for x in raw.split('|') if x.isdigit()]

def _cart_products(request):
    ids=_cart_ids(request)
    return models.Product.objects.filter(id__in=ids) if ids else models.Product.objects.none()

def _cart_count(request): return len(set(_cart_ids(request)))

def _discounted_total(request):
    total=sum(p.price for p in _cart_products(request))
    discount=0; code=request.session.get('coupon_code','')
    if code:
        c=models.Coupon.objects.filter(code__iexact=code,active=True).first()
        if c and (not c.expires_at or c.expires_at >= timezone.now()):
            discount=round(total*c.percent/100)
        else: request.session.pop('coupon_code',None); code=''
    return total,discount,code

@login_required(login_url='login')
@user_passes_test(is_customer, login_url='login')
def all_reviews_view(request):
    reviews = (models.Review.objects
               .select_related('product', 'customer__user')
               .order_by('-created_at'))
    return render(request, 'ecom/all_reviews.html', {
        'reviews': reviews,
        'product_count_in_cart': _cart_count(request),
    })


def product_detail_view(request,pk):
    product=get_object_or_404(models.Product,pk=pk)
    reviews=models.Review.objects.filter(product=product).select_related('customer__user').order_by('-created_at')
    avg=reviews.aggregate(v=Avg('rating'))['v'] or 0
    wished=False
    if request.user.is_authenticated:
        customer=models.Customer.objects.filter(user=request.user).first()
        wished=bool(customer and models.Wishlist.objects.filter(customer=customer,product=product).exists())
    return render(request,'ecom/product_detail.html',{'product':product,'reviews':reviews,'avg_rating':round(avg,1),'product_count_in_cart':_cart_count(request),'wished':wished})

@login_required(login_url='login')
@user_passes_test(is_customer)
def wishlist_view(request):
    customer=get_object_or_404(models.Customer,user=request.user)
    items=models.Wishlist.objects.filter(customer=customer).select_related('product')
    return render(request,'ecom/wishlist.html',{'items':items,'product_count_in_cart':_cart_count(request)})

@login_required(login_url='login')
@user_passes_test(is_customer)
def wishlist_toggle_view(request,pk):
    customer=get_object_or_404(models.Customer,user=request.user); product=get_object_or_404(models.Product,pk=pk)
    item=models.Wishlist.objects.filter(customer=customer,product=product).first()
    if item: item.delete(); messages.info(request,'Removed from wishlist.')
    else: models.Wishlist.objects.create(customer=customer,product=product); messages.success(request,'Added to wishlist.')
    return redirect(request.META.get('HTTP_REFERER','customer-home'))

@login_required(login_url='login')
@user_passes_test(is_customer)
def add_review_view(request,pk):
    product=get_object_or_404(models.Product,pk=pk); customer=get_object_or_404(models.Customer,user=request.user)
    if request.method=='POST':
        rating=max(1,min(5,int(request.POST.get('rating','5')))); comment=request.POST.get('comment','').strip()
        if comment:
            models.Review.objects.update_or_create(customer=customer,product=product,defaults={'rating':rating,'comment':comment})
            messages.success(request,'Your review has been saved.')
    return redirect('product-detail',pk=pk)

@login_required(login_url='login')
@user_passes_test(is_customer)
def address_book_view(request):
    customer=get_object_or_404(models.Customer,user=request.user)
    if request.method=='POST':
        label=request.POST.get('label','Home').strip() or 'Home'; address=request.POST.get('address','').strip(); mobile=request.POST.get('mobile','').strip()
        if address and mobile: models.AddressBook.objects.create(customer=customer,label=label,address=address,mobile=mobile); messages.success(request,'Address saved.')
    addresses=models.AddressBook.objects.filter(customer=customer).order_by('-id')
    return render(request,'ecom/address_book.html',{'addresses':addresses,'product_count_in_cart':_cart_count(request)})

@login_required(login_url='login')
def delete_address_view(request,pk):
    customer=get_object_or_404(models.Customer,user=request.user); models.AddressBook.objects.filter(pk=pk,customer=customer).delete(); return redirect('address-book')

def apply_coupon_view(request):
    code=request.POST.get('code','').strip().upper()
    c=models.Coupon.objects.filter(code=code,active=True).first()
    if c and (not c.expires_at or c.expires_at >= timezone.now()): request.session['coupon_code']=code; messages.success(request,f'Coupon {code} applied.')
    else: request.session.pop('coupon_code',None); messages.error(request,'Invalid or expired coupon.')
    return redirect('cart')

def remove_coupon_view(request): request.session.pop('coupon_code',None); messages.info(request,'Coupon removed.'); return redirect('cart')

@login_required(login_url='login')
@user_passes_test(is_customer)
def order_tracking_view(request,pk):
    customer=get_object_or_404(models.Customer,user=request.user); order=get_object_or_404(models.Orders,pk=pk,customer=customer)
    steps=['Pending','Order Confirmed','Out for Delivery','Delivered']; current=steps.index(order.status) if order.status in steps else 0
    return render(request,'ecom/order_tracking.html',{'order':order,'steps':steps,'current':current,'product_count_in_cart':_cart_count(request)})
