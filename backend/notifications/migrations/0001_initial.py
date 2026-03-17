from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='PushSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_name', models.CharField(blank=True, default='', max_length=120, verbose_name='Пользователь')),
                ('endpoint', models.URLField(unique=True, verbose_name='Endpoint')),
                ('p256dh', models.CharField(max_length=255, verbose_name='P256DH')),
                ('auth', models.CharField(max_length=255, verbose_name='Auth')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
            ],
            options={
                'verbose_name': 'Push-подписка',
                'verbose_name_plural': 'Push-подписки',
                'ordering': ['-updated_at'],
            },
        ),
    ]

