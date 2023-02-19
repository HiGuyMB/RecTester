# Generated by Django 3.2.7 on 2022-02-05 22:54

from django.db import migrations, models
import recapp.models


class Migration(migrations.Migration):

    dependencies = [
        ('recapp', '0006_submission_is_tas'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='is_tas',
            field=models.BooleanField(default=recapp.models.guess_tas, verbose_name='Is TAS'),
        ),
    ]