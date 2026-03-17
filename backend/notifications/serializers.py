from rest_framework import serializers


class PushSubscriptionSerializer(serializers.Serializer):
    user_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    subscription = serializers.DictField()

    def validate_subscription(self, value):
        endpoint = value.get('endpoint')
        keys = value.get('keys') or {}
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')
        if not endpoint or not p256dh or not auth:
            raise serializers.ValidationError('Invalid subscription payload')
        return value

