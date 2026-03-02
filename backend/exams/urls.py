from django.urls import path

from .views import (
    AttemptListAPIView,
    ExamDetailAPIView,
    ExamListAPIView,
    SubmitAttemptAPIView,
    UserStatsAPIView,
)

urlpatterns = [
    path('exams/', ExamListAPIView.as_view(), name='exam-list'),
    path('exams/<int:pk>/', ExamDetailAPIView.as_view(), name='exam-detail'),
    path('exams/<int:exam_id>/submit/', SubmitAttemptAPIView.as_view(), name='exam-submit'),
    path('stats/users/', UserStatsAPIView.as_view(), name='user-stats'),
    path('stats/attempts/', AttemptListAPIView.as_view(), name='attempt-list'),
]
