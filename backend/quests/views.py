from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DutyAssignment, Employee, EmployeeWallet, Quest, QuestCompletion, QuestSubmission
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
