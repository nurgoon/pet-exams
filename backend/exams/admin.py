from urllib.parse import urlencode

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max
from django.forms.models import BaseInlineFormSet
from django.http import HttpResponseRedirect
from django.urls import reverse

from .models import Attempt, AttemptAnswer, Exam, Option, Question


def exam_publication_errors(exam: Exam) -> list[str]:
    if not exam.pk:
        return ['Сначала сохраните экзамен, затем добавьте вопросы и варианты ответов.']

    questions = list(exam.questions.all())
    if not questions:
        return ['Нельзя публиковать экзамен без вопросов.']

    errors: list[str] = []
    for question in questions:
        options = list(question.options.all())
        if not options:
            errors.append(f'Вопрос #{question.id} не содержит вариантов ответов.')
            continue

        if not any(option.is_correct for option in options):
            errors.append(f'Вопрос #{question.id} не содержит правильного варианта.')

    return errors


class OptionInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        active_forms = []
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue

            cleaned = form.cleaned_data
            if cleaned.get('DELETE'):
                continue

            text = cleaned.get('text')
            if text:
                active_forms.append(cleaned)

        if len(active_forms) != 4:
            raise ValidationError('У вопроса должно быть ровно 4 варианта ответа.')

        correct_count = sum(1 for form in active_forms if form.get('is_correct'))
        if correct_count != 1:
            raise ValidationError('Нужно отметить ровно один правильный вариант ответа.')


class OptionInline(admin.TabularInline):
    model = Option
    formset = OptionInlineFormSet
    extra = 0
    fields = ('order', 'text', 'is_correct')

    def get_extra(self, request, obj=None, **kwargs):
        return 4 if obj is None else 0

    class Media:
        js = ('exams/admin_option_sortable.js',)
        css = {'all': ('exams/admin_option_sortable.css',)}


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'exam', 'topic', 'difficulty', 'score_value', 'time_limit_sec', 'order')
    list_filter = ('exam', 'difficulty', 'topic')
    search_fields = ('prompt', 'topic', 'exam__title')
    ordering = ('exam', 'order')
    fieldsets = (
        (
            'Основная информация, вопрос и пояснение',
            {
                'fields': (
                    'exam',
                    'order',
                    'topic',
                    'difficulty',
                    'score_value',
                    'time_limit_sec',
                    'prompt',
                    'explanation',
                ),
                'classes': ('wide',),
            },
        ),
    )
    formfield_overrides = {
        models.TextField: {
            'widget': forms.Textarea(
                attrs={
                    'rows': 4,
                    'cols': 130,
                    'style': 'min-width: 72%; max-width: 100%;',
                }
            )
        },
    }
    inlines = [OptionInline]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'topic':
            formfield.widget.attrs.update(
                {
                    'style': 'width: min(100%, 960px);',
                    'placeholder': 'Например: Техника безопасности, Работа с клиентом, Логистика',
                }
            )
        return formfield

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        exam_id = request.GET.get('exam')
        if exam_id:
            initial['exam'] = exam_id
            last_question = Question.objects.filter(exam_id=exam_id).order_by('-order').first()
            initial['order'] = (last_question.order + 1) if last_question else 1
        return initial

    def save_model(self, request, obj, form, change):
        if not change and obj.exam_id and 'order' not in form.changed_data:
            max_order = (
                Question.objects.filter(exam_id=obj.exam_id).aggregate(max_order=Max('order')).get('max_order') or 0
            )
            obj.order = max_order + 1
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        if '_addanother' in request.POST:
            url = reverse('admin:exams_question_add')
            params = urlencode({'exam': obj.exam_id})
            return HttpResponseRedirect(f'{url}?{params}')
        return super().response_add(request, obj, post_url_continue)


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'subject',
        'subject_color',
        'duration_minutes',
        'default_question_time_sec',
        'effective_duration_minutes_display',
        'passing_score',
        'is_active',
        'questions_count',
    )
    list_filter = ('subject', 'is_active')
    search_fields = ('title', 'subject', 'description')
    actions = ('publish_selected',)
    fields = (
        'title',
        'description',
        'subject',
        'subject_color',
        'duration_minutes',
        'default_question_time_sec',
        'effective_duration_minutes_display',
        'passing_score',
        'is_active',
    )
    readonly_fields = ('effective_duration_minutes_display',)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'subject_color':
            formfield.widget = forms.TextInput(
                attrs={'type': 'color', 'style': 'width: 88px; height: 36px; padding: 2px;'}
            )
        return formfield

    @admin.display(description='Вопросов')
    def questions_count(self, obj):
        return obj.questions.count()

    @admin.display(description='Итоговое время (мин)')
    def effective_duration_minutes_display(self, obj):
        return obj.effective_duration_minutes

    def save_model(self, request, obj, form, change):
        if obj.is_active:
            errors = exam_publication_errors(obj)
            if errors:
                obj.is_active = False
                self.message_user(
                    request,
                    'Экзамен не опубликован: ' + ' | '.join(errors),
                    level='warning',
                )
        super().save_model(request, obj, form, change)

    @admin.action(description='Опубликовать выбранные экзамены')
    def publish_selected(self, request, queryset):
        published = 0
        for exam in queryset:
            errors = exam_publication_errors(exam)
            if errors:
                self.message_user(
                    request,
                    f'Экзамен "{exam.title}" не опубликован: ' + ' | '.join(errors),
                    level='warning',
                )
                continue

            if not exam.is_active:
                exam.is_active = True
                exam.save(update_fields=['is_active'])
            published += 1

        if published:
            self.message_user(request, f'Опубликовано экзаменов: {published}.')


class AttemptAnswerInline(admin.TabularInline):
    model = AttemptAnswer
    extra = 0
    readonly_fields = ('question', 'selected_option', 'is_correct')
    can_delete = False


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user_name',
        'exam',
        'score',
        'scoring_points',
        'max_scoring_points',
        'correct_count',
        'total_questions',
        'duration_seconds',
        'finished_at',
    )
    list_filter = ('exam', 'finished_at', 'user_name')
    search_fields = ('user_name', 'exam__title')
    ordering = ('-finished_at',)
    inlines = [AttemptAnswerInline]


@admin.register(AttemptAnswer)
class AttemptAnswerAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'question', 'selected_option', 'is_correct')
    list_filter = ('is_correct', 'question__exam')
    search_fields = ('attempt__user_name', 'question__prompt', 'question__exam__title')


# Варианты ответов редактируются прямо в вопросе через inline,
# отдельный раздел Option скрыт намеренно, чтобы не ломать UX.

admin.site.site_header = 'Платформа аттестации'
admin.site.site_title = 'Админ-панель'
admin.site.index_title = 'Управление экзаменами и статистикой'

