from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('ecom', '0005_feedback_date'),
    ]
    operations = [
        migrations.AddField(
            model_name='orders',
            name='payment_method',
            field=models.CharField(default='Online Payment', max_length=30),
        ),
    ]
