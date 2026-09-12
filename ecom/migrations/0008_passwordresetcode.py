from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('ecom', '0007_modern_features')]
    operations = [migrations.CreateModel(name='PasswordResetCode', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('email', models.EmailField(db_index=True, max_length=254)), ('code', models.CharField(max_length=6)), ('created_at', models.DateTimeField(auto_now_add=True)), ('expires_at', models.DateTimeField()), ('used', models.BooleanField(default=False))])]
