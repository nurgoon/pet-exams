from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PushSubscription
from .serializers import PushSubscriptionSerializer


class PublicKeyAPIView(APIView):
    def get(self, request):
        key = getattr(settings, 'VAPID_PUBLIC_KEY', '')
        return Response({'public_key': key})


class SubscribeAPIView(APIView):
    def post(self, request):
        serializer = PushSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = serializer.validated_data
        subscription = payload['subscription']
        keys = subscription.get('keys', {})

        user_name = (payload.get('user_name') or '').strip()
        endpoint = subscription.get('endpoint')
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')

        obj, _ = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'user_name': user_name,
                'p256dh': p256dh,
                'auth': auth,
            },
        )

        return Response({'id': obj.id, 'status': 'ok'})


class TestPushAPIView(APIView):
    def post(self, request):
        if not getattr(settings, 'VAPID_PRIVATE_KEY', ''):
            return Response({'detail': 'VAPID keys not configured'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from pywebpush import webpush, WebPushException
        except Exception as exc:
            return Response({'detail': f'pywebpush missing: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        user_name = (request.data.get('user_name') or '').strip()
        title = request.data.get('title') or 'Protocol'
        body = request.data.get('body') or 'Test notification'

        qs = PushSubscription.objects.all()
        if user_name:
            qs = qs.filter(user_name=user_name)

        sent = 0
        failed = 0
        for sub in qs:
            subscription_info = {
                'endpoint': sub.endpoint,
                'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
            }
            try:
                webpush(
                    subscription_info,
                    data={'title': title, 'body': body},
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={'sub': settings.VAPID_SUBJECT},
                )
                sent += 1
            except WebPushException:
                failed += 1

        return Response({'sent': sent, 'failed': failed})

