# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-08-10 17:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emplacement', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emplacementenddate',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], max_length=1, null=True),
        ),
        migrations.AlterField(
            model_name='emplacementorganization',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], max_length=1, null=True),
        ),
        migrations.AlterField(
            model_name='emplacementsite',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], max_length=1, null=True),
        ),
        migrations.AlterField(
            model_name='emplacementstartdate',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], max_length=1, null=True),
        ),
    ]