from __future__ import annotations

from django.http import JsonResponse
from urllib.parse import unquote

from quests.models import Employee
from quests.utils import normalize_phone


class ApiPhoneVerificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ''
        if not path.startswith('/api/'):
            return self.get_response(request)
        if path.startswith('/api/auth/'):
            return self.get_response(request)

        raw_name = (request.headers.get('X-User-Name') or '').strip()
        user_name = unquote(raw_name) if raw_name else ''
        user_phone = (request.headers.get('X-User-Phone') or '').strip()
        if not user_name or not user_phone:
            return JsonResponse({'detail': 'phone verification required'}, status=401)

        normalized_phone = normalize_phone(user_phone)
        if not normalized_phone:
            return JsonResponse({'detail': 'invalid phone'}, status=400)

        employee = Employee.objects.filter(
            name=user_name,
            phone=normalized_phone,
            phone_verified=True,
        ).first()
        if not employee:
            return JsonResponse({'detail': 'phone verification required'}, status=403)

        request.employee = employee
        return self.get_response(request)
