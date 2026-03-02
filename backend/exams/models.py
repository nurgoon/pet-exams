from django.db import models, transaction
from django.db.models import F


class Exam(models.Model):
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    subject = models.CharField('Направление', max_length=100)
    subject_color = models.CharField('Цвет темы', max_length=7, default='#2563eb')
    duration_minutes = models.PositiveIntegerField('Длительность (мин)', default=20)
    default_question_time_sec = models.PositiveIntegerField(
        'Время на вопрос по умолчанию (сек)',
        null=True,
        blank=True,
        help_text='Если у вопроса не задано время, будет использовано это значение.',
    )
    passing_score = models.PositiveIntegerField('Порог прохождения (%)', default=70)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    class Meta:
        ordering = ['title']
        verbose_name = 'Экзамен'
        verbose_name_plural = 'Экзамены'

    def __str__(self) -> str:
        return self.title

    @property
    def effective_duration_seconds(self) -> int:
        default_time = self.default_question_time_sec
        questions = list(self.questions.all())
        if questions and default_time:
            return sum((question.time_limit_sec or default_time) for question in questions)
        return int(self.duration_minutes * 60)

    @property
    def effective_duration_minutes(self) -> int:
        seconds = self.effective_duration_seconds
        return max(1, (seconds + 59) // 60)


class Question(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Легкий'),
        ('medium', 'Средний'),
        ('hard', 'Сложный'),
    ]

    exam = models.ForeignKey(Exam, verbose_name='Экзамен', on_delete=models.CASCADE, related_name='questions')
    prompt = models.TextField('Вопрос')
    explanation = models.TextField('Пояснение для разбора', blank=True)
    topic = models.CharField('Тема', max_length=100)
    difficulty = models.CharField('Сложность', max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    score_value = models.PositiveIntegerField('Баллы за вопрос', default=1)
    time_limit_sec = models.PositiveIntegerField('Время на вопрос (сек)', null=True, blank=True)
    order = models.PositiveIntegerField('Порядок', default=1)

    class Meta:
        ordering = ['exam_id', 'order', 'id']
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'

    def __str__(self) -> str:
        return f'{self.exam.title}: {self.prompt[:50]}'

    def save(self, *args, **kwargs):
        requested_order = max(1, int(self.order or 1))

        with transaction.atomic():
            if self.pk:
                previous = (
                    Question.objects.select_for_update()
                    .only('id', 'exam_id', 'order')
                    .get(pk=self.pk)
                )
                old_exam_id = previous.exam_id
                old_order = previous.order

                max_order_in_target = (
                    Question.objects.filter(exam_id=self.exam_id)
                    .exclude(pk=self.pk)
                    .aggregate(max_order=models.Max('order'))
                    .get('max_order')
                    or 0
                )
                target_order = min(requested_order, max_order_in_target + 1)
                self.order = target_order

                if old_exam_id == self.exam_id:
                    if target_order != old_order:
                        (
                            Question.objects.filter(
                                exam_id=self.exam_id,
                                order=target_order,
                            )
                            .exclude(pk=self.pk)
                            .update(order=old_order)
                        )
                else:
                    Question.objects.filter(
                        exam_id=old_exam_id,
                        order__gt=old_order,
                    ).update(order=F('order') - 1)
                    Question.objects.filter(
                        exam_id=self.exam_id,
                        order__gte=target_order,
                    ).update(order=F('order') + 1)
            else:
                max_order_in_target = (
                    Question.objects.filter(exam_id=self.exam_id)
                    .aggregate(max_order=models.Max('order'))
                    .get('max_order')
                    or 0
                )
                target_order = min(requested_order, max_order_in_target + 1)
                self.order = target_order
                Question.objects.filter(
                    exam_id=self.exam_id,
                    order__gte=target_order,
                ).update(order=F('order') + 1)

            return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        exam_id = self.exam_id
        order = self.order
        with transaction.atomic():
            result = super().delete(*args, **kwargs)
            Question.objects.filter(exam_id=exam_id, order__gt=order).update(order=F('order') - 1)
            return result


class Option(models.Model):
    question = models.ForeignKey(Question, verbose_name='Вопрос', on_delete=models.CASCADE, related_name='options')
    text = models.CharField('Текст варианта', max_length=300)
    is_correct = models.BooleanField('Правильный ответ', default=False)
    order = models.PositiveIntegerField('Порядок', default=1)

    class Meta:
        ordering = ['question_id', 'order', 'id']
        verbose_name = 'Вариант ответа'
        verbose_name_plural = 'Варианты ответов'

    def __str__(self) -> str:
        return self.text


class Attempt(models.Model):
    exam = models.ForeignKey(Exam, verbose_name='Экзамен', on_delete=models.PROTECT, related_name='attempts')
    user_name = models.CharField('Имя пользователя', max_length=100, db_index=True)
    started_at = models.DateTimeField('Начало прохождения')
    finished_at = models.DateTimeField('Окончание прохождения', auto_now_add=True)
    score = models.PositiveIntegerField('Результат (%)')
    scoring_points = models.PositiveIntegerField('Скоринговый балл', default=0)
    max_scoring_points = models.PositiveIntegerField('Макс. скоринговый балл', default=0)
    correct_count = models.PositiveIntegerField('Правильных ответов')
    total_questions = models.PositiveIntegerField('Всего вопросов')
    duration_seconds = models.PositiveIntegerField('Время (сек)', default=0)

    class Meta:
        ordering = ['-finished_at']
        verbose_name = 'Попытка'
        verbose_name_plural = 'Попытки'

    def __str__(self) -> str:
        return f'{self.user_name} - {self.exam.title} ({self.score}%)'


class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(Attempt, verbose_name='Попытка', on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, verbose_name='Вопрос', on_delete=models.PROTECT)
    selected_option = models.ForeignKey(
        Option,
        verbose_name='Выбранный вариант',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    is_correct = models.BooleanField('Ответ верный', default=False)

    class Meta:
        unique_together = ('attempt', 'question')
        verbose_name = 'Ответ в попытке'
        verbose_name_plural = 'Ответы в попытках'

    def __str__(self) -> str:
        return f'Попытка {self.attempt_id} / Вопрос {self.question_id}'

