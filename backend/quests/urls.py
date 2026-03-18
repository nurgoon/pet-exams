from django.urls import path

from .views import (
    CompleteQuestAPIView,
    DutyListAPIView,
    QuestLeaderboardAPIView,
    QuestListAPIView,
    QuestProfileAPIView,
    RequestSmsCodeAPIView,
    SubmitQuestAPIView,
    VerifySmsCodeAPIView,
    RequestCallCheckAPIView,
    VerifyCallCheckAPIView,
)

urlpatterns = [
    path('auth/request_code/', RequestSmsCodeAPIView.as_view(), name='auth-request-code'),
    path('auth/verify_code/', VerifySmsCodeAPIView.as_view(), name='auth-verify-code'),
    path('auth/request_call/', RequestCallCheckAPIView.as_view(), name='auth-request-call'),
    path('auth/check_call/', VerifyCallCheckAPIView.as_view(), name='auth-check-call'),
    path('quests/profile/', QuestProfileAPIView.as_view(), name='quest-profile'),
    path('quests/', QuestListAPIView.as_view(), name='quest-list'),
    path('quests/<int:quest_id>/complete/', CompleteQuestAPIView.as_view(), name='quest-complete'),
    path('quests/<int:quest_id>/submit/', SubmitQuestAPIView.as_view(), name='quest-submit'),
    path('quests/leaderboard/', QuestLeaderboardAPIView.as_view(), name='quest-leaderboard'),
    path('duties/', DutyListAPIView.as_view(), name='duty-list'),
]
