from django.db import models
from django.contrib.auth.models import User

class Customer(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE)
    profile_pic=models.ImageField(upload_to='profile_pic/CustomerProfilePic/',null=True,blank=True)
    address=models.CharField(max_length=255)
    mobile=models.CharField(max_length=20)
    @property
    def get_name(self): return (self.user.first_name+" "+self.user.last_name).strip() or self.user.username
    @property
    def get_id(self): return self.user.id
    def __str__(self): return self.get_name

class Product(models.Model):
    name=models.CharField(max_length=100)
    product_image=models.ImageField(upload_to='product_image/',null=True,blank=True)
    price=models.PositiveIntegerField()
    description=models.CharField(max_length=255)
    category=models.CharField(max_length=80,default='General')
    stock=models.PositiveIntegerField(default=25)
    created_at=models.DateTimeField(auto_now_add=True,null=True)
    def __str__(self): return self.name

class Orders(models.Model):
    STATUS=(('Pending','Pending'),('Order Confirmed','Order Confirmed'),('Out for Delivery','Out for Delivery'),('Delivered','Delivered'))
    customer=models.ForeignKey('Customer',on_delete=models.CASCADE,null=True)
    product=models.ForeignKey('Product',on_delete=models.CASCADE,null=True)
    email=models.CharField(max_length=50,null=True)
    address=models.CharField(max_length=500,null=True)
    mobile=models.CharField(max_length=20,null=True)
    order_date=models.DateField(auto_now_add=True,null=True)
    status=models.CharField(max_length=50,null=True,choices=STATUS)
    payment_method=models.CharField(max_length=30,default='Online Payment')
    coupon_code=models.CharField(max_length=40,blank=True,default='')
    discount=models.PositiveIntegerField(default=0)

class Feedback(models.Model):
    name=models.CharField(max_length=40)
    feedback=models.CharField(max_length=500)
    date=models.DateField(auto_now_add=True,null=True)
    def __str__(self): return self.name

class Wishlist(models.Model):
    customer=models.ForeignKey(Customer,on_delete=models.CASCADE,related_name='wishlist')
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=('customer','product')

class Review(models.Model):
    customer=models.ForeignKey(Customer,on_delete=models.CASCADE,related_name='reviews')
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='reviews')
    rating=models.PositiveSmallIntegerField(default=5)
    comment=models.CharField(max_length=500)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=('customer','product')

class AddressBook(models.Model):
    customer=models.ForeignKey(Customer,on_delete=models.CASCADE,related_name='addresses')
    label=models.CharField(max_length=30,default='Home')
    address=models.CharField(max_length=500)
    mobile=models.CharField(max_length=20)
    created_at=models.DateTimeField(auto_now_add=True)

class Coupon(models.Model):
    code=models.CharField(max_length=30,unique=True)
    percent=models.PositiveSmallIntegerField(default=10)
    active=models.BooleanField(default=True)
    expires_at=models.DateTimeField(null=True,blank=True)
    def __str__(self): return self.code


class PasswordResetCode(models.Model):
    email=models.EmailField(db_index=True)
    code=models.CharField(max_length=6)
    created_at=models.DateTimeField(auto_now_add=True)
    expires_at=models.DateTimeField()
    used=models.BooleanField(default=False)

    def __str__(self):
        return f"Password reset for {self.email}"
