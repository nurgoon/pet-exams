from django.urls import path

from .views import (
    CompleteQuestAPIView,
    DutyListAPIView,
    QuestLeaderboardAPIView,
    QuestListAPIView,
    QuestProfileAPIView,
    SubmitQuestAPIView,
)

urlpatterns = [
    path('quests/profile/', QuestProfileAPIView.as_view(), name='quest-profile'),
    path('quests/', QuestListAPIView.as_view(), name='quest-list'),
    path('quests/<int:quest_id>/complete/', CompleteQuestAPIView.as_view(), name='quest-complete'),
    path('quests/<int:quest_id>/submit/', SubmitQuestAPIView.as_view(), name='quest-submit'),
    path('quests/leaderboard/', QuestLeaderboardAPIView.as_view(), name='quest-leaderboard'),
    path('duties/', DutyListAPIView.as_view(), name='duty-list'),
]
