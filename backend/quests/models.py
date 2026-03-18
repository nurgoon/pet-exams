from __future__ import annotations

from datetime import date
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import models, transaction
from django.db.models import Q
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from PIL import Image


def compress_image(field_file, max_side: int = 1600, quality: int = 78) -> ContentFile:
    image = Image.open(field_file)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.thumbnail((max_side, max_side), Image.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return ContentFile(buffer.getvalue())


class Employee(models.Model):
    name = models.CharField('Сотрудник', max_length=120, unique=True, db_index=True)
    phone = models.CharField('Phone', max_length=32, blank=True, default='', db_index=True)
    phone_verified = models.BooleanField('Phone verified', default=False)
    phone_code_hash = models.CharField('Phone code hash', max_length=128, blank=True, default='')
    phone_code_expires_at = models.DateTimeField('Phone code expires at', null=True, blank=True)
    phone_code_attempts = models.IntegerField('Phone code attempts', default=0)
    phone_code_last_sent_at = models.DateTimeField('Phone code last sent at', null=True, blank=True)
    phone_call_check_id = models.CharField('Phone call check id', max_length=64, blank=True, default='')
    phone_call_expires_at = models.DateTimeField('Phone call expires at', null=True, blank=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'

    def __str__(self) -> str:
        return self.name


class EmployeeWallet(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='wallet')
    exp = models.IntegerField('Опыт (EXP)', default=0)
    rub_cents = models.IntegerField('Баланс (коп.)', default=0)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    class Meta:
        verbose_name = 'Баланс сотрудника'
        verbose_name_plural = 'Баланс сотрудников'

    def __str__(self) -> str:
        rub = self.rub_cents / 100
        return f'{self.employee.name}: {self.exp} EXP, {rub:.2f} ₽'


class Quest(models.Model):
    REPEAT_CHOICES = [
        ('daily', 'Ежедневно'),
        ('once', 'Один раз'),
    ]

    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    category = models.CharField('Категория', max_length=80, blank=True, default='')
    repeat = models.CharField('Повтор', max_length=10, choices=REPEAT_CHOICES, default='daily')
    reward_exp = models.IntegerField('Награда EXP', default=0)
    reward_rub_cents = models.IntegerField('Награда (коп.)', default=0)
    requires_approval = models.BooleanField('Требует проверки', default=False)
    requires_proof = models.BooleanField('Нужен скриншот/фото', default=False)
    is_active = models.BooleanField('Активно', default=True)
    sort_order = models.IntegerField('Порядок', default=100)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        ordering = ['sort_order', 'title']
        verbose_name = 'Квест / задача'
        verbose_name_plural = 'Квесты / задачи'

    def __str__(self) -> str:
        return self.title

    def completion_date_key(self, business_date: date) -> date:
        if self.repeat == 'once':
            return date(1970, 1, 1)
        return business_date


class QuestCompletion(models.Model):
    quest = models.ForeignKey(Quest, on_delete=models.PROTECT, related_name='completions')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='quest_completions')
    business_date = models.DateField('Дата (для повторов)', db_index=True)
    completed_at = models.DateTimeField('Время выполнения', auto_now_add=True)
    notes = models.TextField('Комментарий', blank=True, default='')

    class Meta:
        verbose_name = 'Выполнение'
        verbose_name_plural = 'Выполнения'
        constraints = [
            models.UniqueConstraint(
                fields=['quest', 'employee', 'business_date'],
                name='uniq_quest_completion',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.employee.name}: {self.quest.title} ({self.business_date})'

    @staticmethod
    def award_completion(*, employee: Employee, quest: Quest, business_date: date, notes: str = '') -> tuple[QuestCompletion, bool]:
        completion_date = quest.completion_date_key(business_date)

        with transaction.atomic():
            wallet, _ = EmployeeWallet.objects.select_for_update().get_or_create(employee=employee)
            completion, created = QuestCompletion.objects.get_or_create(
                quest=quest,
                employee=employee,
                business_date=completion_date,
                defaults={'notes': notes},
            )

            if not created:
                return completion, False

            wallet.exp = int(wallet.exp) + int(quest.reward_exp or 0)
            wallet.rub_cents = int(wallet.rub_cents) + int(quest.reward_rub_cents or 0)
            wallet.save(update_fields=['exp', 'rub_cents', 'updated_at'])
            return completion, True


class QuestSubmission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'На проверке'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]

    quest = models.ForeignKey(Quest, on_delete=models.PROTECT, related_name='submissions')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='quest_submissions')
    business_date = models.DateField('Дата (ключ)', db_index=True)
    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES, default='pending', db_index=True)
    proof_image = models.ImageField('Скриншот/фото', upload_to='quest_proofs/%Y/%m/%d/', null=True, blank=True)
    notes = models.TextField('Комментарий', blank=True, default='')
    review_comment = models.TextField('Комментарий проверяющего', blank=True, default='')
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    reviewed_at = models.DateTimeField('Проверено', null=True, blank=True)

    class Meta:
        verbose_name = 'Отправка на проверку'
        verbose_name_plural = 'Отправки на проверку'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['quest', 'employee', 'business_date'],
                condition=Q(status='pending'),
                name='uniq_pending_quest_submission',
            ),
        ]

    def save(self, *args, **kwargs) -> None:
        if self.proof_image:
            is_new = self._state.adding
            if not is_new and self.pk:
                old = QuestSubmission.objects.filter(pk=self.pk).first()
                if old and old.proof_image != self.proof_image:
                    is_new = True
            if is_new:
                compressed = compress_image(self.proof_image)
                self.proof_image.save(self.proof_image.name, compressed, save=False)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.employee.name}: {self.quest.title} ({self.business_date}) [{self.status}]'


@receiver(post_delete, sender=QuestSubmission)
def delete_proof_on_delete(sender, instance: QuestSubmission, **kwargs) -> None:
    if instance.proof_image:
        instance.proof_image.delete(save=False)


@receiver(pre_save, sender=QuestSubmission)
def delete_old_proof_on_change(sender, instance: QuestSubmission, **kwargs) -> None:
    if not instance.pk:
        return
    old = QuestSubmission.objects.filter(pk=instance.pk).first()
    if old and old.proof_image and old.proof_image != instance.proof_image:
        old.proof_image.delete(save=False)

class DutyAssignment(models.Model):
    DUTY_CHOICES = [
        ('cleaning', 'Уборка'),
    ]

    duty_type = models.CharField('Тип', max_length=20, choices=DUTY_CHOICES, default='cleaning', db_index=True)
    business_date = models.DateField('Дата', db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='duties')
    notes = models.TextField('Комментарий', blank=True, default='')
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Дежурство'
        verbose_name_plural = 'Дежурства'
        ordering = ['-business_date', 'duty_type']
        constraints = [
            models.UniqueConstraint(fields=['duty_type', 'business_date'], name='uniq_duty_by_date'),
        ]

    def __str__(self) -> str:
        return f'{self.get_duty_type_display()} {self.business_date}: {self.employee.name}'


