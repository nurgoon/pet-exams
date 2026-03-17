from __future__ import annotations

from datetime import date

from rest_framework import serializers

from .models import DutyAssignment, Employee, EmployeeWallet, Quest, QuestCompletion, QuestSubmission


class QuestSerializer(serializers.ModelSerializer):
    completed = serializers.BooleanField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    submission_status = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)
    submission_id = serializers.IntegerField(read_only=True, allow_null=True)
    submitted_at = serializers.DateTimeField(read_only=True, allow_null=True)
    reviewed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    review_comment = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)

    class Meta:
        model = Quest
        fields = [
            'id',
            'title',
            'description',
            'category',
            'repeat',
            'reward_exp',
            'reward_rub_cents',
            'requires_approval',
            'requires_proof',
            'completed',
            'completed_at',
            'submission_status',
            'submission_id',
            'submitted_at',
            'reviewed_at',
            'review_comment',
        ]


class QuestProfileSerializer(serializers.Serializer):
    user_name = serializers.CharField()
    exp = serializers.IntegerField()
    rub_cents = serializers.IntegerField()
    completed_today = serializers.IntegerField()


class CompleteQuestSerializer(serializers.Serializer):
    user_name = serializers.CharField()
    business_date = serializers.DateField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_user_name(self, value: str) -> str:
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('user_name is required')
        if len(value) > 120:
            raise serializers.ValidationError('user_name too long')
        return value

    def validate_business_date(self, value: date) -> date:
        # Minimal sanity: allow only reasonable range.
        if value.year < 2000 or value.year > 2100:
            raise serializers.ValidationError('business_date out of range')
        return value


class QuestCompletionResultSerializer(serializers.Serializer):
    created = serializers.BooleanField()
    exp = serializers.IntegerField()
    rub_cents = serializers.IntegerField()
    completion = serializers.DictField()


class LeaderboardEntrySerializer(serializers.Serializer):
    user_name = serializers.CharField()
    exp = serializers.IntegerField()
    rub_cents = serializers.IntegerField()


class SubmitQuestSerializer(CompleteQuestSerializer):
    proof_image = serializers.ImageField(required=False, allow_null=True)


class DutyAssignmentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='employee.name', read_only=True)

    class Meta:
        model = DutyAssignment
        fields = ['id', 'duty_type', 'business_date', 'user_name', 'notes']
