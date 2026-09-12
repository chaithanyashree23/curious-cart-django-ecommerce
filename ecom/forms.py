from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from . import models


class CustomerUserForm(forms.ModelForm):
    email = forms.EmailField(required=False)
    password = forms.CharField(required=False, min_length=8, widget=forms.PasswordInput(render_value=False))
    class Meta:
        model=User
        fields=['first_name','last_name','email','username','password']
        widgets = {
        'password': forms.PasswordInput()
        }
        
    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not self.instance.pk and not password:
            raise forms.ValidationError('Password is required.')
        if password and len(password) < 8:
            raise forms.ValidationError('Password must contain at least 8 characters.')
        return password

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        qs = User.objects.filter(username__iexact=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('This username is already in use. Please choose another.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not self.instance.pk and not email:
            raise forms.ValidationError('Email address is required for a new account.')
        if not email:
            return email
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('This email is already registered. Please use another email.')
        return email


class CustomerForm(forms.ModelForm):
    class Meta:
        model=models.Customer
        fields=['address','mobile']

class ProductForm(forms.ModelForm):
    class Meta:
        model=models.Product
        fields=['name','price','description','stock','product_image']

#address of shipment
class AddressForm(forms.Form):
    Email = forms.EmailField()
    Mobile= forms.IntegerField()
    Address = forms.CharField(max_length=500)

class FeedbackForm(forms.ModelForm):
    class Meta:
        model=models.Feedback
        fields=['name','feedback']

#for updating status of order
class OrderForm(forms.ModelForm):
    class Meta:
        model=models.Orders
        fields=['status']

#for contact us page
class ContactusForm(forms.Form):
    Name = forms.CharField(max_length=30)
    Email = forms.EmailField()
    Message = forms.CharField(max_length=500,widget=forms.Textarea(attrs={'rows': 3, 'cols': 30}))


class CustomerLoginForm(forms.Form):
    identifier = forms.CharField(label='Username or email', max_length=254)
    password = forms.CharField(widget=forms.PasswordInput, strip=False)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        identifier = cleaned.get('identifier', '').strip()
        password = cleaned.get('password')
        if not identifier or not password:
            raise forms.ValidationError('Please enter your username/email and password.')
        user = User.objects.filter(email__iexact=identifier).first()
        username = user.username if user else identifier
        self.user_cache = authenticate(self.request, username=username, password=password)
        if self.user_cache is None:
            raise forms.ValidationError('Incorrect username/email or password. Please try again.')
        if not self.user_cache.is_active:
            raise forms.ValidationError('This account is inactive. Please contact the administrator.')
        if not self.user_cache.groups.filter(name='CUSTOMER').exists():
            raise forms.ValidationError('This login is for customer accounts. Please use the Admin sign in for staff accounts.')
        return cleaned

    def get_user(self):
        return self.user_cache
