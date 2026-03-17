from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PushMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_name', models.CharField(blank=True, default='', max_length=120, verbose_name='Пользователь')),
                ('title', models.CharField(max_length=200, verbose_name='Заголовок')),
                ('body', models.TextField(verbose_name='Сообщение')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('sent_at', models.DateTimeField(blank=True, null=True, verbose_name='Отправлено')),
                ('status', models.CharField(default='pending', max_length=20, verbose_name='Статус')),
                ('error', models.TextField(blank=True, default='', verbose_name='Ошибка')),
            ],
            options={
                'verbose_name': 'Push-уведомление',
                'verbose_name_plural': 'Push-уведомления',
                'ordering': ['-created_at'],
            },
        ),
    ]

