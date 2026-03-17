from __future__ import annotations

from datetime import date, timedelta
import os

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DutyAssignment, Employee, EmployeeWallet, Quest, QuestCompletion, QuestSubmission
from .utils import can_send_sms, generate_sms_code, hash_sms_code, normalize_phone, send_sms_ru
from .serializers import (
    CompleteQuestSerializer,
    DutyAssignmentSerializer,
    LeaderboardEntrySerializer,
    SubmitQuestSerializer,
    QuestProfileSerializer,
    QuestSerializer,
)


def _get_business_date(request) -> date:
    raw = request.query_params.get('business_date')
    if raw:
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return timezone.localdate()
    return timezone.localdate()


class QuestProfileAPIView(APIView):
    def get(self, request):
        user_name = (request.query_params.get('user_name') or '').strip()
        if not user_name:
            return Response({'detail': 'user_name query param required'}, status=status.HTTP_400_BAD_REQUEST)

        employee, _ = Employee.objects.get_or_create(name=user_name)
        wallet, _ = EmployeeWallet.objects.get_or_create(employee=employee)
        business_date = _get_business_date(request)

        completed_today = QuestCompletion.objects.filter(employee=employee, business_date=business_date).count()
        return Response(
            QuestProfileSerializer(
                {
                    'user_name': employee.name,
                    'exp': wallet.exp,
                    'rub_cents': wallet.rub_cents,
                    'completed_today': completed_today,
                }
            ).data
        )


class QuestListAPIView(APIView):
    def get(self, request):
        user_name = (request.query_params.get('user_name') or '').strip()
        business_date = _get_business_date(request)

        quest_list = list(Quest.objects.filter(is_active=True).order_by('sort_order', 'title'))
        if not user_name:
            for quest in quest_list:
                setattr(quest, 'completed', False)
                setattr(quest, 'completed_at', None)
                setattr(quest, 'submission_status', None)
                setattr(quest, 'submission_id', None)
                setattr(quest, 'submitted_at', None)
                setattr(quest, 'reviewed_at', None)
                setattr(quest, 'review_comment', None)
            return Response(QuestSerializer(quest_list, many=True).data)

        employee, _ = Employee.objects.get_or_create(name=user_name)

        quest_ids = [quest.id for quest in quest_list]
        daily_key = business_date
        once_key = date(1970, 1, 1)

        completions = QuestCompletion.objects.filter(
            employee=employee,
            quest_id__in=quest_ids,
            business_date__in=[daily_key, once_key],
        ).select_related('quest')
        completion_by_key = {(row.quest_id, row.business_date): row for row in completions}

        submissions = (
            QuestSubmission.objects.filter(
                employee=employee,
                quest_id__in=quest_ids,
                business_date__in=[daily_key, once_key],
            )
            .order_by('-created_at')
            .select_related('quest')
        )
        submission_by_key: dict[tuple[int, date], QuestSubmission] = {}
        for row in submissions:
            key = (row.quest_id, row.business_date)
            if key not in submission_by_key:
                submission_by_key[key] = row

        for quest in quest_list:
            key_date = quest.completion_date_key(business_date)
            completion = completion_by_key.get((quest.id, key_date))
            submission = submission_by_key.get((quest.id, key_date))

            setattr(quest, 'completed', bool(completion))
            setattr(quest, 'completed_at', completion.completed_at if completion else None)
            setattr(quest, 'submission_status', submission.status if submission else None)
            setattr(quest, 'submission_id', submission.id if submission else None)
            setattr(quest, 'submitted_at', submission.created_at if submission else None)
            setattr(quest, 'reviewed_at', submission.reviewed_at if submission else None)
            setattr(quest, 'review_comment', submission.review_comment if submission else None)

        return Response(QuestSerializer(quest_list, many=True).data)


class CompleteQuestAPIView(APIView):
    def post(self, request, quest_id: int):
        serializer = CompleteQuestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            quest = Quest.objects.get(pk=quest_id, is_active=True)
        except Quest.DoesNotExist:
            return Response({'detail': 'Quest not found'}, status=status.HTTP_404_NOT_FOUND)

        if quest.requires_approval or quest.requires_proof:
            return Response(
                {'detail': 'Quest requires approval. Use submit endpoint.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        business_date = serializer.validated_data.get('business_date') or timezone.localdate()
        user_name = serializer.validated_data['user_name']
        notes = serializer.validated_data.get('notes') or ''

        employee, _ = Employee.objects.get_or_create(name=user_name)
        completion, created = QuestCompletion.award_completion(
            employee=employee,
            quest=quest,
            business_date=business_date,
            notes=notes,
        )

        wallet, _ = EmployeeWallet.objects.get_or_create(employee=employee)

        return Response(
            {
                'created': created,
                'exp': wallet.exp,
                'rub_cents': wallet.rub_cents,
                'completion': {
                    'id': completion.id,
                    'quest_id': quest.id,
                    'business_date': str(completion.business_date),
                    'completed_at': completion.completed_at.isoformat(),
                },
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class SubmitQuestAPIView(APIView):
    def post(self, request, quest_id: int):
        serializer = SubmitQuestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            quest = Quest.objects.get(pk=quest_id, is_active=True)
        except Quest.DoesNotExist:
            return Response({'detail': 'Quest not found'}, status=status.HTTP_404_NOT_FOUND)

        business_date = serializer.validated_data.get('business_date') or timezone.localdate()
        user_name = serializer.validated_data['user_name']
        notes = serializer.validated_data.get('notes') or ''
        proof_image = serializer.validated_data.get('proof_image')

        employee, _ = Employee.objects.get_or_create(name=user_name)
        date_key = quest.completion_date_key(business_date)

        already_completed = QuestCompletion.objects.filter(
            employee=employee,
            quest=quest,
            business_date=date_key,
        ).exists()
        if already_completed:
            return Response({'detail': 'Quest already completed.'}, status=status.HTTP_400_BAD_REQUEST)

        pending = QuestSubmission.objects.filter(
            employee=employee,
            quest=quest,
            business_date=date_key,
            status='pending',
        ).first()
        if pending:
            return Response(
                {
                    'created': False,
                    'submission': {
                        'id': pending.id,
                        'status': pending.status,
                        'business_date': str(pending.business_date),
                        'created_at': pending.created_at.isoformat(),
                    },
                },
                status=status.HTTP_200_OK,
            )

        if quest.requires_proof and not proof_image:
            return Response({'detail': 'proof_image is required'}, status=status.HTTP_400_BAD_REQUEST)

        if not (quest.requires_approval or quest.requires_proof):
            completion, created = QuestCompletion.award_completion(
                employee=employee,
                quest=quest,
                business_date=date_key,
                notes=notes,
            )
            wallet, _ = EmployeeWallet.objects.get_or_create(employee=employee)
            return Response(
                {
                    'created': created,
                    'auto_approved': True,
                    'exp': wallet.exp,
                    'rub_cents': wallet.rub_cents,
                    'completion': {
                        'id': completion.id,
                        'quest_id': quest.id,
                        'business_date': str(completion.business_date),
                        'completed_at': completion.completed_at.isoformat(),
                    },
                },
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )

        submission = QuestSubmission.objects.create(
            quest=quest,
            employee=employee,
            business_date=date_key,
            status='pending',
            proof_image=proof_image,
            notes=notes,
        )

        return Response(
            {
                'created': True,
                'submission': {
                    'id': submission.id,
                    'status': submission.status,
                    'business_date': str(submission.business_date),
                    'created_at': submission.created_at.isoformat(),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class QuestLeaderboardAPIView(APIView):
    def get(self, request):
        top = int(request.query_params.get('top') or 25)
        top = max(1, min(top, 100))

        qs = (
            EmployeeWallet.objects.select_related('employee')
            .order_by('-exp', '-rub_cents', 'employee__name')[:top]
        )
        data = [
            {'user_name': row.employee.name, 'exp': row.exp, 'rub_cents': row.rub_cents}
            for row in qs
        ]
        return Response(LeaderboardEntrySerializer(data, many=True).data)


class DutyListAPIView(APIView):
    def get(self, request):
        duty_type = (request.query_params.get('duty_type') or 'cleaning').strip()
        raw_days = request.query_params.get('days')
        days = int(raw_days) if raw_days else 7
        days = max(1, min(days, 31))

        raw_from = request.query_params.get('from')
        if raw_from:
            try:
                from_date = date.fromisoformat(raw_from)
            except ValueError:
                from_date = timezone.localdate()
        else:
            from_date = timezone.localdate()

        to_date = from_date + timedelta(days=days - 1)

        qs = (
            DutyAssignment.objects.select_related('employee')
            .filter(duty_type=duty_type, business_date__gte=from_date, business_date__lte=to_date)
            .order_by('business_date', 'duty_type')
        )
        return Response(DutyAssignmentSerializer(qs, many=True).data)


class RequestSmsCodeAPIView(APIView):
    def post(self, request):
        user_name = (request.data.get('user_name') or '').strip()
        raw_phone = (request.data.get('phone') or '').strip()
        if not user_name:
            return Response({'detail': 'user_name required'}, status=status.HTTP_400_BAD_REQUEST)

        phone = normalize_phone(raw_phone)
        if not phone:
            return Response({'detail': 'invalid phone'}, status=status.HTTP_400_BAD_REQUEST)

        api_key = os.getenv('SMSRU_API_KEY', '').strip()
        sender = os.getenv('SMSRU_SENDER', '').strip()
        if not api_key:
            return Response({'detail': 'SMS service not configured'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        ttl_minutes = int(os.getenv('SMS_CODE_TTL_MINUTES', '5'))
        length = int(os.getenv('SMS_CODE_LENGTH', '4'))
        cooldown = int(os.getenv('SMS_CODE_COOLDOWN_SECONDS', '60'))

        employee, _ = Employee.objects.get_or_create(name=user_name)
        if employee.phone_verified and employee.phone and employee.phone != phone:
            return Response({'detail': 'phone mismatch'}, status=status.HTTP_403_FORBIDDEN)

        if not can_send_sms(employee.phone_code_last_sent_at, cooldown):
            return Response({'detail': 'code already sent, try later'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        code = generate_sms_code(length)
        employee.phone = phone
        employee.phone_code_hash = hash_sms_code(phone, code)
        employee.phone_code_expires_at = timezone.now() + timedelta(minutes=ttl_minutes)
        employee.phone_code_attempts = 0
        employee.phone_code_last_sent_at = timezone.now()
        employee.phone_verified = False
        employee.save(
            update_fields=[
                'phone',
                'phone_code_hash',
                'phone_code_expires_at',
                'phone_code_attempts',
                'phone_code_last_sent_at',
                'phone_verified',
                'updated_at',
            ]
        )

        message = f'Код подтверждения: {code}'
        response_text = send_sms_ru(api_key=api_key, sender=sender, phone=phone, message=message)
        if not response_text.startswith('100'):
            return Response({'detail': 'sms failed', 'provider': response_text}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({'sent': True, 'expires_in': ttl_minutes * 60})


class VerifySmsCodeAPIView(APIView):
    def post(self, request):
        user_name = (request.data.get('user_name') or '').strip()
        raw_phone = (request.data.get('phone') or '').strip()
        code = (request.data.get('code') or '').strip()
        if not user_name or not raw_phone or not code:
            return Response({'detail': 'user_name, phone, code required'}, status=status.HTTP_400_BAD_REQUEST)

        phone = normalize_phone(raw_phone)
        if not phone:
            return Response({'detail': 'invalid phone'}, status=status.HTTP_400_BAD_REQUEST)

        employee = Employee.objects.filter(name=user_name).first()
        if not employee:
            return Response({'detail': 'user not found'}, status=status.HTTP_404_NOT_FOUND)

        if employee.phone != phone:
            return Response({'detail': 'phone mismatch'}, status=status.HTTP_403_FORBIDDEN)

        if not employee.phone_code_hash or not employee.phone_code_expires_at:
            return Response({'detail': 'code not requested'}, status=status.HTTP_400_BAD_REQUEST)

        if employee.phone_code_expires_at < timezone.now():
            return Response({'detail': 'code expired'}, status=status.HTTP_400_BAD_REQUEST)

        max_attempts = int(os.getenv('SMS_CODE_MAX_ATTEMPTS', '5'))
        if employee.phone_code_attempts >= max_attempts:
            return Response({'detail': 'too many attempts'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        expected = hash_sms_code(phone, code)
        if expected != employee.phone_code_hash:
            employee.phone_code_attempts += 1
            employee.save(update_fields=['phone_code_attempts', 'updated_at'])
            return Response({'detail': 'invalid code'}, status=status.HTTP_400_BAD_REQUEST)

        employee.phone_verified = True
        employee.phone_code_hash = ''
        employee.phone_code_expires_at = None
        employee.phone_code_attempts = 0
        employee.save(
            update_fields=[
                'phone_verified',
                'phone_code_hash',
                'phone_code_expires_at',
                'phone_code_attempts',
                'updated_at',
            ]
        )

        return Response({'verified': True})
