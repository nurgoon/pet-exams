from django.conf import settings
from django.contrib import admin
from django.utils import timezone

from .models import PushMessage, PushSubscription


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    search_fields = ['user_name', 'endpoint']
    list_display = ['user_name', 'endpoint', 'updated_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PushMessage)
class PushMessageAdmin(admin.ModelAdmin):
    list_display = ['title', 'user_name', 'status', 'created_at', 'sent_at']
    search_fields = ['title', 'body', 'user_name']

    def save_model(self, request, obj, form, change):
        obj.status = 'sending'
        obj.error = ''
        super().save_model(request, obj, form, change)

        if not getattr(settings, 'VAPID_PRIVATE_KEY', ''):
            obj.status = 'error'
            obj.error = 'VAPID keys not configured'
            obj.save(update_fields=['status', 'error'])
            return

        try:
            from pywebpush import webpush, WebPushException
        except Exception as exc:
            obj.status = 'error'
            obj.error = f'pywebpush missing: {exc}'
            obj.save(update_fields=['status', 'error'])
            return

        qs = PushSubscription.objects.all()
        if obj.user_name:
            qs = qs.filter(user_name=obj.user_name)

        sent = 0
        failed = 0
        for sub in qs:
            subscription_info = {
                'endpoint': sub.endpoint,
                'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
            }
            try:
                payload = json.dumps({'title': obj.title, 'body': obj.body})
                webpush(
                    subscription_info,
                    data=payload,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={'sub': settings.VAPID_SUBJECT},
                )
                sent += 1
            except WebPushException as exc:
                failed += 1
                obj.error = f'{obj.error}\n{sub.endpoint}: {exc}'

        obj.sent_at = timezone.now()
        obj.status = 'sent' if failed == 0 else f'partial ({sent}/{sent + failed})'
        obj.save(update_fields=['sent_at', 'status', 'error'])
import json
