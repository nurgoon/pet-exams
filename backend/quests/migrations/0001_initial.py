from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Employee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=120, unique=True, verbose_name='Сотрудник')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлен')),
            ],
            options={
                'verbose_name': 'Сотрудник',
                'verbose_name_plural': 'Сотрудники',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Quest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Название')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('category', models.CharField(blank=True, default='', max_length=80, verbose_name='Категория')),
                (
                    'repeat',
                    models.CharField(
                        choices=[('daily', 'Ежедневно'), ('once', 'Один раз')],
                        default='daily',
                        max_length=10,
                        verbose_name='Повтор',
                    ),
                ),
                ('reward_exp', models.IntegerField(default=0, verbose_name='Награда EXP')),
                ('reward_rub_cents', models.IntegerField(default=0, verbose_name='Награда (коп.)')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активно')),
                ('sort_order', models.IntegerField(default=100, verbose_name='Порядок')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
            ],
            options={
                'verbose_name': 'Квест / задача',
                'verbose_name_plural': 'Квесты / задачи',
                'ordering': ['sort_order', 'title'],
            },
        ),
        migrations.CreateModel(
            name='EmployeeWallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('exp', models.IntegerField(default=0, verbose_name='Опыт (EXP)')),
                ('rub_cents', models.IntegerField(default=0, verbose_name='Баланс (коп.)')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлен')),
                (
                    'employee',
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='wallet', to='quests.employee'),
                ),
            ],
            options={
                'verbose_name': 'Баланс сотрудника',
                'verbose_name_plural': 'Баланс сотрудников',
            },
        ),
        migrations.CreateModel(
            name='QuestCompletion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('business_date', models.DateField(db_index=True, verbose_name='Дата (для повторов)')),
                ('completed_at', models.DateTimeField(auto_now_add=True, verbose_name='Время выполнения')),
                ('notes', models.TextField(blank=True, default='', verbose_name='Комментарий')),
                (
                    'employee',
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quest_completions', to='quests.employee'),
                ),
                (
                    'quest',
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='completions', to='quests.quest'),
                ),
            ],
            options={
                'verbose_name': 'Выполнение',
                'verbose_name_plural': 'Выполнения',
            },
        ),
        migrations.AddConstraint(
            model_name='questcompletion',
            constraint=models.UniqueConstraint(fields=('quest', 'employee', 'business_date'), name='uniq_quest_completion'),
        ),
    ]

