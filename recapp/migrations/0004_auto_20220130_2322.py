# Generated by Django 3.2.7 on 2022-01-30 23:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recapp', '0003_auto_20220130_2321'),
    ]

    operations = [
        migrations.AlterField(
            model_name='run',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='score',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='submission',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]