from django.db import models


class PushSubscription(models.Model):
    user_name = models.CharField('Пользователь', max_length=120, blank=True, default='')
    endpoint = models.URLField('Endpoint', unique=True)
    p256dh = models.CharField('P256DH', max_length=255)
    auth = models.CharField('Auth', max_length=255)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Push-подписка'
        verbose_name_plural = 'Push-подписки'
        ordering = ['-updated_at']

    def __str__(self) -> str:
        return f'{self.user_name or "Unknown"}: {self.endpoint[:32]}'


class PushMessage(models.Model):
    user_name = models.CharField('Пользователь', max_length=120, blank=True, default='')
    title = models.CharField('Заголовок', max_length=200)
    body = models.TextField('Сообщение')
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    sent_at = models.DateTimeField('Отправлено', null=True, blank=True)
    status = models.CharField('Статус', max_length=20, default='pending')
    error = models.TextField('Ошибка', blank=True, default='')

    class Meta:
        verbose_name = 'Push-уведомление'
        verbose_name_plural = 'Push-уведомления'
        ordering = ['-created_at']

    def __str__(self) -> str:
        target = self.user_name or 'all'
        return f'{self.title} -> {target}'
