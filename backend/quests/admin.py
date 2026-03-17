from django.contrib import admin, messages
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import DutyAssignment, Employee, EmployeeWallet, Quest, QuestCompletion, QuestSubmission


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_display = ['name', 'created_at', 'updated_at']


@admin.register(EmployeeWallet)
class EmployeeWalletAdmin(admin.ModelAdmin):
    search_fields = ['employee__name']
    list_display = ['employee', 'exp', 'rub_cents', 'updated_at']
    list_select_related = ['employee']


@admin.register(Quest)
class QuestAdmin(admin.ModelAdmin):
    search_fields = ['title', 'category']
    list_filter = ['repeat', 'is_active', 'category']
    list_display = [
        'title',
        'category',
        'repeat',
        'reward_exp',
        'reward_rub_cents',
        'requires_approval',
        'requires_proof',
        'is_active',
        'sort_order',
    ]
    ordering = ['sort_order', 'title']


@admin.register(QuestCompletion)
class QuestCompletionAdmin(admin.ModelAdmin):
    search_fields = ['employee__name', 'quest__title']
    list_filter = ['business_date', 'quest__repeat', 'quest__category']
    list_display = ['employee', 'quest', 'business_date', 'completed_at']
    list_select_related = ['employee', 'quest']


@admin.action(description='Одобрить и начислить награду')
def approve_submissions(modeladmin, request, queryset):
    for submission in queryset.select_related('employee', 'quest'):
        if submission.status != 'pending':
            continue
        completion, _ = QuestCompletion.award_completion(
            employee=submission.employee,
            quest=submission.quest,
            business_date=submission.business_date,
            notes=submission.notes,
        )
        submission.status = 'approved'
        submission.reviewed_at = timezone.now()
        submission.save(update_fields=['status', 'reviewed_at'])


@admin.action(description='Отклонить (без начисления)')
def reject_submissions(modeladmin, request, queryset):
    now = timezone.now()
    queryset.filter(status='pending').update(status='rejected', reviewed_at=now)


@admin.register(QuestSubmission)
class QuestSubmissionAdmin(admin.ModelAdmin):
    search_fields = ['employee__name', 'quest__title']
    list_filter = ['status', 'business_date', 'quest__category', 'quest__repeat']
    list_display = [
        'quest_link',
        'employee',
        'business_date',
        'status',
        'proof_thumbnail',
        'created_at',
        'reviewed_at',
        'quick_actions',
    ]
    list_display_links = None
    list_select_related = ['employee', 'quest']
    actions = [approve_submissions, reject_submissions]

    @admin.display(description='Квест', ordering='quest__title')
    def quest_link(self, obj):
        url = reverse('admin:quests_questsubmission_change', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.quest.title)

    def get_list_display_links(self, request, list_display):
        return ()

    @admin.display(description='Фото')
    def proof_thumbnail(self, obj):
        if not obj.proof_image:
            return '—'
        return format_html(
            '<a href="{0}" target="_blank"><img src="{0}" style="height:40px;width:auto;border-radius:4px;object-fit:cover;" /></a>',
            obj.proof_image.url,
        )

    @admin.display(description='Быстро')
    def quick_actions(self, obj):
        if obj.status != 'pending':
            return '—'
        approve_url = reverse('admin:quests_questsubmission_quick_approve', args=[obj.pk])
        reject_url = reverse('admin:quests_questsubmission_quick_reject', args=[obj.pk])
        return format_html(
            '<a class="button" href="{0}">Одобрить</a>&nbsp;'
            '<a class="button" style="background:#b02a37;border-color:#b02a37" href="{1}">Отклонить</a>',
            approve_url,
            reject_url,
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:submission_id>/quick-approve/',
                self.admin_site.admin_view(self.quick_approve),
                name='quests_questsubmission_quick_approve',
            ),
            path(
                '<int:submission_id>/quick-reject/',
                self.admin_site.admin_view(self.quick_reject),
                name='quests_questsubmission_quick_reject',
            ),
        ]
        return custom_urls + urls

    def quick_approve(self, request, submission_id):
        submission = QuestSubmission.objects.select_related('employee', 'quest').filter(pk=submission_id).first()
        if not submission:
            self.message_user(request, 'Отправка не найдена.', level=messages.ERROR)
            return self._redirect_back(request)
        if submission.status != 'pending':
            self.message_user(request, 'Отправка уже обработана.', level=messages.WARNING)
            return self._redirect_back(request)
        QuestCompletion.award_completion(
            employee=submission.employee,
            quest=submission.quest,
            business_date=submission.business_date,
            notes=submission.notes,
        )
        submission.status = 'approved'
        submission.reviewed_at = timezone.now()
        submission.save(update_fields=['status', 'reviewed_at'])
        self.message_user(request, 'Отправка одобрена и награда начислена.', level=messages.SUCCESS)
        return self._redirect_back(request)

    def quick_reject(self, request, submission_id):
        submission = QuestSubmission.objects.filter(pk=submission_id).first()
        if not submission:
            self.message_user(request, 'Отправка не найдена.', level=messages.ERROR)
            return self._redirect_back(request)
        if submission.status != 'pending':
            self.message_user(request, 'Отправка уже обработана.', level=messages.WARNING)
            return self._redirect_back(request)
        submission.status = 'rejected'
        submission.reviewed_at = timezone.now()
        submission.save(update_fields=['status', 'reviewed_at'])
        self.message_user(request, 'Отправка отклонена.', level=messages.SUCCESS)
        return self._redirect_back(request)

    @staticmethod
    def _redirect_back(request):
        from django.shortcuts import redirect

        return redirect(request.META.get('HTTP_REFERER', 'admin:quests_questsubmission_changelist'))


@admin.register(DutyAssignment)
class DutyAssignmentAdmin(admin.ModelAdmin):
    search_fields = ['employee__name', 'notes']
    list_filter = ['duty_type', 'business_date']
    list_display = ['duty_type', 'business_date', 'employee', 'updated_at']
    list_select_related = ['employee']
