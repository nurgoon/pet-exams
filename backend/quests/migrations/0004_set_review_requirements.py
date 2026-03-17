from django.db import migrations


def set_requirements(apps, schema_editor):
    Quest = apps.get_model('quests', 'Quest')

    proof_titles = [
        'Уборка полов торгового помещения',
        'Проверка и публикация объявлений на досках',
        'Проверка баланса IP-телефонии',
    ]

    Quest.objects.filter(title__in=proof_titles).update(requires_approval=True, requires_proof=True)


def unset_requirements(apps, schema_editor):
    Quest = apps.get_model('quests', 'Quest')
    Quest.objects.filter(requires_approval=True, requires_proof=True).update(requires_approval=False, requires_proof=False)


class Migration(migrations.Migration):
    dependencies = [
        ('quests', '0003_quest_requires_approval_quest_requires_proof_and_more'),
    ]

    operations = [
        migrations.RunPython(set_requirements, unset_requirements),
    ]

