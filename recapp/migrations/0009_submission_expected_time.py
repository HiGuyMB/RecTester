# Generated by Django 3.2.7 on 2022-02-05 22:44
import re
from django.db import migrations, models

import recapp.models


def expected_time(apps, schema_editor):
    Submission = apps.get_model('recapp', 'Submission')
    for sub in Submission.objects.all():
        if sub.expected_time is None:
            sub.expected_time = recapp.models.guess_time(sub)
            sub.save()


class Migration(migrations.Migration):

    dependencies = [
        ('recapp', '0008_alter_run_os'),
    ]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='expected_time',
            field=models.IntegerField('Expected Time', default=None, null=True),
            preserve_default=False,
        ),
        migrations.RunPython(expected_time)
    ]
