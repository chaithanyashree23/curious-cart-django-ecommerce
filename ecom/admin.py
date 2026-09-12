from django.contrib import admin
from .models import Customer,Product,Orders,Feedback,Wishlist,Review,AddressBook,Coupon
for m in [Customer,Product,Orders,Feedback,Wishlist,Review,AddressBook,Coupon]: admin.site.register(m)
