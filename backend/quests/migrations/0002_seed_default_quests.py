from django.db import migrations


def seed_quests(apps, schema_editor):
    Quest = apps.get_model('quests', 'Quest')

    defaults = [
        {
            'title': 'Открыть смену',
            'category': 'Смена',
            'repeat': 'daily',
            'reward_exp': 10,
            'reward_rub_cents': 0,
            'description': 'Подготовить рабочее место и открыть смену.',
            'sort_order': 10,
        },
        {
            'title': 'Обзвонить клиентов с незакрытыми договорами',
            'category': 'Продажи',
            'repeat': 'daily',
            'reward_exp': 25,
            'reward_rub_cents': 0,
            'description': 'Сделать прозвон по списку и зафиксировать результат.',
            'sort_order': 20,
        },
        {
            'title': 'Уборка полов торгового помещения',
            'category': 'Чистота',
            'repeat': 'daily',
            'reward_exp': 15,
            'reward_rub_cents': 0,
            'description': 'Выполнить уборку согласно расписанию (ответственный дня).',
            'sort_order': 30,
        },
        {
            'title': 'Проверка и публикация объявлений на досках',
            'category': 'Маркетинг',
            'repeat': 'daily',
            'reward_exp': 20,
            'reward_rub_cents': 0,
            'description': 'Avito / doska.ykt.ru / youla.ru: обновить/опубликовать объявления.',
            'sort_order': 40,
        },
        {
            'title': 'Проверка баланса IP-телефонии',
            'category': 'Связь',
            'repeat': 'daily',
            'reward_exp': 10,
            'reward_rub_cents': 0,
            'description': 'Проверить баланс и при необходимости пополнить/сообщить ответственному.',
            'sort_order': 50,
        },
    ]

    for item in defaults:
        Quest.objects.get_or_create(
            title=item['title'],
            defaults=item,
        )


def unseed_quests(apps, schema_editor):
    Quest = apps.get_model('quests', 'Quest')
    titles = [
        'Открыть смену',
        'Обзвонить клиентов с незакрытыми договорами',
        'Уборка полов торгового помещения',
        'Проверка и публикация объявлений на досках',
        'Проверка баланса IP-телефонии',
    ]
    Quest.objects.filter(title__in=titles).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('quests', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_quests, unseed_quests),
    ]

