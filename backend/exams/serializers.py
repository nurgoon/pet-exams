from rest_framework import serializers

from .models import Attempt, AttemptAnswer, Exam, Option, Question


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ('id', 'text', 'order')


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ('id', 'prompt', 'explanation', 'topic', 'difficulty', 'score_value', 'time_limit_sec', 'order', 'options')


class ExamListSerializer(serializers.ModelSerializer):
    questions_count = serializers.IntegerField(source='questions.count', read_only=True)
    effective_duration_minutes = serializers.IntegerField(read_only=True)
    effective_duration_seconds = serializers.IntegerField(read_only=True)

    class Meta:
        model = Exam
        fields = (
            'id',
            'title',
            'description',
            'subject',
            'subject_color',
            'duration_minutes',
            'effective_duration_minutes',
            'effective_duration_seconds',
            'passing_score',
            'questions_count',
        )


class ExamDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    effective_duration_minutes = serializers.IntegerField(read_only=True)
    effective_duration_seconds = serializers.IntegerField(read_only=True)

    class Meta:
        model = Exam
        fields = (
            'id',
            'title',
            'description',
            'subject',
            'subject_color',
            'duration_minutes',
            'effective_duration_minutes',
            'effective_duration_seconds',
            'passing_score',
            'questions',
        )


class AttemptAnswerReviewSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    prompt = serializers.CharField()
    topic = serializers.CharField()
    explanation = serializers.CharField()
    score_value = serializers.IntegerField()
    selected_option_id = serializers.IntegerField(allow_null=True)
    selected_text = serializers.CharField()
    correct_option_id = serializers.IntegerField()
    correct_text = serializers.CharField()
    is_correct = serializers.BooleanField()


class SubmitAttemptSerializer(serializers.Serializer):
    user_name = serializers.CharField(max_length=100)
    started_at = serializers.DateTimeField(required=False)
    duration_seconds = serializers.IntegerField(required=False, min_value=0)
    answers = serializers.DictField(child=serializers.IntegerField(), allow_empty=True)


class AttemptSerializer(serializers.ModelSerializer):
    exam_title = serializers.CharField(source='exam.title', read_only=True)

    class Meta:
        model = Attempt
        fields = (
            'id',
            'exam',
            'exam_title',
            'user_name',
            'started_at',
            'finished_at',
            'score',
            'scoring_points',
            'max_scoring_points',
            'correct_count',
            'total_questions',
            'duration_seconds',
        )


class UserStatSerializer(serializers.Serializer):
    user_name = serializers.CharField()
    attempts_count = serializers.IntegerField()
    best_score = serializers.IntegerField()
    avg_score = serializers.FloatField()
    avg_duration_seconds = serializers.FloatField()

