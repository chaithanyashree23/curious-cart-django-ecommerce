
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from ecom import views
from django.contrib.auth.views import LogoutView
urlpatterns = [
    path('admin/', admin.site.urls),
    path('',views.home_view,name=''),
    path('afterlogin', views.afterlogin_view,name='afterlogin'),
    path('logout', LogoutView.as_view(template_name='ecom/logout.html'),name='logout'),
    path('aboutus', views.aboutus_view),
    path('contactus', views.contactus_view,name='contactus'),
    path('search', views.search_view,name='search'),
    path('send-feedback', views.send_feedback_view,name='send-feedback'),

    

    path('adminclick', views.adminclick_view),
    path('login', views.customer_login_view, name='login'),
    path('adminlogin', views.admin_login_view, name='adminlogin'),
    path('admin-change-password', views.admin_change_password_view, name='admin-change-password'),
    path('admin-edit-profile', views.admin_edit_profile_view, name='admin-edit-profile'),
    path('admin-dashboard', views.admin_dashboard_view,name='admin-dashboard'),
    path('admin-reviews', views.admin_reviews_view, name='admin-reviews'),

    path('view-customer', views.view_customer_view,name='view-customer'),
    path('delete-customer/<int:pk>', views.delete_customer_view,name='delete-customer'),
    path('update-customer/<int:pk>', views.update_customer_view,name='update-customer'),

    path('admin-products', views.admin_products_view,name='admin-products'),
    path('admin-add-product', views.admin_add_product_view,name='admin-add-product'),
    path('delete-product/<int:pk>', views.delete_product_view,name='delete-product'),
    path('update-product/<int:pk>', views.update_product_view,name='update-product'),

    path('admin-view-booking', views.admin_view_booking_view,name='admin-view-booking'),
    path('delete-order/<int:pk>', views.delete_order_view,name='delete-order'),
    path('update-order/<int:pk>', views.update_order_view,name='update-order'),


    path('customersignup', views.customer_signup_view, name='customersignup'),
    path('customerlogin', views.customer_login_view, name='customerlogin'),
    path('forgot-password', views.customer_password_reset_request_view, name='forgot-password'),
    path('verify-reset-code', views.customer_password_reset_verify_view, name='verify-reset-code'),
    path('customer-home', views.customer_home_view,name='customer-home'),
    path('my-order', views.my_order_view,name='my-order'),
    path('my-profile', views.my_profile_view,name='my-profile'),
    path('edit-profile', views.edit_profile_view,name='edit-profile'),
    path('download-invoice/<int:orderID>/<int:productID>', views.download_invoice_view,name='download-invoice'),


    path('add-to-cart/<int:pk>', views.add_to_cart_view,name='add-to-cart'),
    path('cart', views.cart_view,name='cart'),
    path('remove-from-cart/<int:pk>', views.remove_from_cart_view,name='remove-from-cart'),
    path('customer-address', views.customer_address_view,name='customer-address'),
    path('payment', views.payment_view, name='payment'),
    path('payment-success', views.payment_success_view,name='payment-success'),
    path('product/<int:pk>', views.product_detail_view, name='product-detail'),
    path('reviews', views.all_reviews_view, name='all-reviews'),
    path('wishlist', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:pk>', views.wishlist_toggle_view, name='wishlist-toggle'),
    path('product/<int:pk>/review', views.add_review_view, name='add-review'),
    path('addresses', views.address_book_view, name='address-book'),
    path('addresses/delete/<int:pk>', views.delete_address_view, name='delete-address'),
    path('coupon/apply', views.apply_coupon_view, name='apply-coupon'),
    path('coupon/remove', views.remove_coupon_view, name='remove-coupon'),
    path('order-tracking/<int:pk>', views.order_tracking_view, name='order-tracking'),


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

