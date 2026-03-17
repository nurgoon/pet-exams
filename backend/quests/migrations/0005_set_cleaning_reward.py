from django.db import migrations


def set_cleaning_reward(apps, schema_editor):
    Quest = apps.get_model('quests', 'Quest')
    Quest.objects.filter(title='Уборка полов торгового помещения').update(reward_rub_cents=40000)


def unset_cleaning_reward(apps, schema_editor):
    Quest = apps.get_model('quests', 'Quest')
    Quest.objects.filter(title='Уборка полов торгового помещения', reward_rub_cents=40000).update(reward_rub_cents=0)


class Migration(migrations.Migration):
    dependencies = [
        ('quests', '0004_set_review_requirements'),
    ]

    operations = [
        migrations.RunPython(set_cleaning_reward, unset_cleaning_reward),
    ]
