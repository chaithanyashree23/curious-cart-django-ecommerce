from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[('ecom','0006_orders_payment_method')]
    operations=[
        migrations.AddField(model_name='product',name='category',field=models.CharField(default='General',max_length=80)),
        migrations.AddField(model_name='product',name='stock',field=models.PositiveIntegerField(default=25)),
        migrations.AddField(model_name='product',name='created_at',field=models.DateTimeField(auto_now_add=True,null=True)),
        migrations.AddField(model_name='orders',name='coupon_code',field=models.CharField(blank=True,default='',max_length=40)),
        migrations.AddField(model_name='orders',name='discount',field=models.PositiveIntegerField(default=0)),
        migrations.CreateModel(name='Wishlist',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('created_at',models.DateTimeField(auto_now_add=True)),('customer',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='wishlist',to='ecom.customer')),('product',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,to='ecom.product'))]),
        migrations.CreateModel(name='Review',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('rating',models.PositiveSmallIntegerField(default=5)),('comment',models.CharField(max_length=500)),('created_at',models.DateTimeField(auto_now_add=True)),('customer',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='reviews',to='ecom.customer')),('product',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='reviews',to='ecom.product'))]),
        migrations.CreateModel(name='AddressBook',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('label',models.CharField(default='Home',max_length=30)),('address',models.CharField(max_length=500)),('mobile',models.CharField(max_length=20)),('created_at',models.DateTimeField(auto_now_add=True)),('customer',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='addresses',to='ecom.customer'))]),
        migrations.CreateModel(name='Coupon',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('code',models.CharField(max_length=30,unique=True)),('percent',models.PositiveSmallIntegerField(default=10)),('active',models.BooleanField(default=True)),('expires_at',models.DateTimeField(blank=True,null=True))]),
        migrations.AlterUniqueTogether(name='wishlist',unique_together={('customer','product')}),
        migrations.AlterUniqueTogether(name='review',unique_together={('customer','product')}),
    ]

