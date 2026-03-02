from django.db.models import Avg, Count, Max
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Attempt, AttemptAnswer, Exam, Option
from .serializers import (
    AttemptSerializer,
    ExamDetailSerializer,
    ExamListSerializer,
    SubmitAttemptSerializer,
    UserStatSerializer,
)


class ExamListAPIView(generics.ListAPIView):
    queryset = Exam.objects.filter(is_active=True).prefetch_related('questions')
    serializer_class = ExamListSerializer


class ExamDetailAPIView(generics.RetrieveAPIView):
    queryset = Exam.objects.filter(is_active=True).prefetch_related('questions__options')
    serializer_class = ExamDetailSerializer


class SubmitAttemptAPIView(APIView):
    def post(self, request, exam_id: int):
        serializer = SubmitAttemptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            exam = Exam.objects.prefetch_related('questions__options').get(id=exam_id, is_active=True)
        except Exam.DoesNotExist:
            return Response({'detail': 'Exam not found.'}, status=status.HTTP_404_NOT_FOUND)

        payload = serializer.validated_data
        answers = payload.get('answers', {})
        questions = list(exam.questions.all())

        if not questions:
            return Response({'detail': 'Exam has no questions.'}, status=status.HTTP_400_BAD_REQUEST)

        option_by_id = {
            option.id: option for question in questions for option in question.options.all()
        }

        reviews = []
        correct_count = 0
        scoring_points = 0
        max_scoring_points = sum(question.score_value for question in questions)

        started_at = payload.get('started_at') or timezone.now()
        duration_seconds = payload.get('duration_seconds', 0)

        attempt = Attempt.objects.create(
            exam=exam,
            user_name=payload['user_name'].strip() or 'Student',
            started_at=started_at,
            score=0,
            scoring_points=0,
            max_scoring_points=max_scoring_points,
            correct_count=0,
            total_questions=len(questions),
            duration_seconds=duration_seconds,
        )

        attempt_answers = []
        for question in questions:
            correct_option = next((opt for opt in question.options.all() if opt.is_correct), None)
            selected_option_id = answers.get(str(question.id)) or answers.get(question.id)
            selected_option = option_by_id.get(selected_option_id)

            is_correct = bool(correct_option and selected_option and selected_option.id == correct_option.id)
            if is_correct:
                correct_count += 1
                scoring_points += question.score_value

            attempt_answers.append(
                AttemptAnswer(
                    attempt=attempt,
                    question=question,
                    selected_option=selected_option,
                    is_correct=is_correct,
                )
            )

            reviews.append(
                {
                    'question_id': question.id,
                    'prompt': question.prompt,
                    'topic': question.topic,
                    'explanation': question.explanation,
                    'score_value': question.score_value,
                    'selected_option_id': selected_option.id if selected_option else None,
                    'selected_text': selected_option.text if selected_option else 'Не выбран',
                    'correct_option_id': correct_option.id if correct_option else None,
                    'correct_text': correct_option.text if correct_option else 'Не задан',
                    'is_correct': is_correct,
                }
            )

        AttemptAnswer.objects.bulk_create(attempt_answers)

        score = round((correct_count / len(questions)) * 100)
        attempt.score = score
        attempt.scoring_points = scoring_points
        attempt.max_scoring_points = max_scoring_points
        attempt.correct_count = correct_count
        attempt.save(update_fields=['score', 'scoring_points', 'max_scoring_points', 'correct_count'])

        return Response(
            {
                'attempt': AttemptSerializer(attempt).data,
                'exam_title': exam.title,
                'passing_score': exam.passing_score,
                'reviews': reviews,
            },
            status=status.HTTP_201_CREATED,
        )


class UserStatsAPIView(APIView):
    def get(self, request):
        stats = (
            Attempt.objects.values('user_name')
            .annotate(
                attempts_count=Count('id'),
                best_score=Max('score'),
                avg_score=Avg('score'),
                avg_duration_seconds=Avg('duration_seconds'),
            )
            .order_by('-best_score', '-avg_score')
        )

        return Response(UserStatSerializer(stats, many=True).data)


class AttemptListAPIView(generics.ListAPIView):
    serializer_class = AttemptSerializer

    def get_queryset(self):
        qs = Attempt.objects.select_related('exam').order_by('-finished_at')
        user_name = self.request.query_params.get('user_name')
        if user_name:
            qs = qs.filter(user_name=user_name)
        return qs[:100]
