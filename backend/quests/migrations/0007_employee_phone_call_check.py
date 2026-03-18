from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('quests', '0006_employee_phone_verification'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='phone_call_check_id',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='Phone call check id'),
        ),
        migrations.AddField(
            model_name='employee',
            name='phone_call_expires_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Phone call expires at'),
        ),
    ]
