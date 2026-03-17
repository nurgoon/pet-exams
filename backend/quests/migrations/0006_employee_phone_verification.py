from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('quests', '0005_set_cleaning_reward'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='phone',
            field=models.CharField(blank=True, db_index=True, default='', max_length=32, verbose_name='Phone'),
        ),
        migrations.AddField(
            model_name='employee',
            name='phone_verified',
            field=models.BooleanField(default=False, verbose_name='Phone verified'),
        ),
        migrations.AddField(
            model_name='employee',
            name='phone_code_hash',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='Phone code hash'),
        ),
        migrations.AddField(
            model_name='employee',
            name='phone_code_expires_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Phone code expires at'),
        ),
        migrations.AddField(
            model_name='employee',
            name='phone_code_attempts',
            field=models.IntegerField(default=0, verbose_name='Phone code attempts'),
        ),
        migrations.AddField(
            model_name='employee',
            name='phone_code_last_sent_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Phone code last sent at'),
        ),
    ]
