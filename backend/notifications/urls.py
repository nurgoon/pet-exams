from django.urls import path

from .views import PublicKeyAPIView, SubscribeAPIView, TestPushAPIView

urlpatterns = [
    path('push/public-key/', PublicKeyAPIView.as_view(), name='push-public-key'),
    path('push/subscribe/', SubscribeAPIView.as_view(), name='push-subscribe'),
    path('push/test/', TestPushAPIView.as_view(), name='push-test'),
]

