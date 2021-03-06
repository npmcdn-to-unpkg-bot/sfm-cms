# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-06-28 21:56
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('source', '0009_auto_20160615_1511'),
        ('violation', '0002_auto_20151102_2237'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='violationsource',
            name='source',
        ),
        migrations.RemoveField(
            model_name='violationsource',
            name='violation',
        ),
        migrations.AddField(
            model_name='violationadminlevel1',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
        migrations.AddField(
            model_name='violationadminlevel1',
            name='lang',
            field=models.CharField(max_length=5, null=True),
        ),
        migrations.AddField(
            model_name='violationadminlevel1',
            name='sources',
            field=models.ManyToManyField(related_name='violation_violationadminlevel1_related', to='source.Source'),
        ),
        migrations.AddField(
            model_name='violationadminlevel2',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
        migrations.AddField(
            model_name='violationadminlevel2',
            name='lang',
            field=models.CharField(max_length=5, null=True),
        ),
        migrations.AddField(
            model_name='violationadminlevel2',
            name='sources',
            field=models.ManyToManyField(related_name='violation_violationadminlevel2_related', to='source.Source'),
        ),
        migrations.AddField(
            model_name='violationdescription',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
        migrations.AddField(
            model_name='violationdescription',
            name='lang',
            field=models.CharField(max_length=5, null=True),
        ),
        migrations.AddField(
            model_name='violationdescription',
            name='sources',
            field=models.ManyToManyField(related_name='violation_violationdescription_related', to='source.Source'),
        ),
        migrations.AddField(
            model_name='violationenddate',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
        migrations.AddField(
            model_name='violationenddate',
            name='lang',
            field=models.CharField(max_length=5, null=True),
        ),
        migrations.AddField(
            model_name='violationenddate',
            name='sources',
            field=models.ManyToManyField(related_name='violation_violationenddate_related', to='source.Source'),
        ),
        migrations.AddField(
            model_name='violationgeoname',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
        migrations.AddField(
            model_name='violationgeoname',
            name='lang',
            field=models.CharField(max_length=5, null=True),
        ),
        migrations.AddField(
            model_name='violationgeoname',
            name='sources',
            field=models.ManyToManyField(related_name='violation_violationgeoname_related', to='source.Source'),
        ),
        migrations.AddField(
            model_name='violationgeonameid',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
        migrations.AddField(
            model_name='violationgeonameid',
            name='lang',
            field=models.CharField(max_length=5, null=True),
        ),
        migrations.AddField(
            model_name='violationgeonameid',
            name='sources',
            field=models.ManyToManyField(related_name='violation_violationgeonameid_related', to='source.Source'),
        ),
        migrations.AddField(
            model_name='violationlocation',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
        migrations.AddField(
            model_name='violationlocation',
            name='lang',
            field=models.CharField(max_length=5, null=True),
        ),
        migrations.AddField(
            model_name='violationlocation',
            name='sources',
            field=models.ManyToManyField(related_name='violation_violationlocation_related', to='source.Source'),
        ),
        migrations.AddField(
            model_name='violationperpetrator',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
        migrations.AddField(
            model_name='violationperpetrator',
            name='lang',
            field=models.CharField(max_length=5, null=True),
        ),
        migrations.AddField(
            model_name='violationperpetrator',
            name='sources',
            field=models.ManyToManyField(related_name='violation_violationperpetrator_related', to='source.Source'),
        ),
        migrations.AddField(
            model_name='violationperpetratororganization',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
        migrations.AddField(
            model_name='violationperpetratororganization',
            name='lang',
            field=models.CharField(max_length=5, null=True),
        ),
        migrations.AddField(
            model_name='violationperpetratororganization',
            name='sources',
            field=models.ManyToManyField(related_name='violation_violationperpetratororganization_related', to='source.Source'),
        ),
        migrations.AddField(
            model_name='violationstartdate',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
        migrations.AddField(
            model_name='violationstartdate',
            name='lang',
            field=models.CharField(max_length=5, null=True),
        ),
        migrations.AddField(
            model_name='violationstartdate',
            name='sources',
            field=models.ManyToManyField(related_name='violation_violationstartdate_related', to='source.Source'),
        ),
        migrations.AddField(
            model_name='violationtype',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
        migrations.AddField(
            model_name='violationtype',
            name='lang',
            field=models.CharField(max_length=5, null=True),
        ),
        migrations.AddField(
            model_name='violationtype',
            name='sources',
            field=models.ManyToManyField(related_name='violation_violationtype_related', to='source.Source'),
        ),
        migrations.AlterField(
            model_name='violationperpetrator',
            name='value',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='person.Person'),
        ),
        migrations.AlterField(
            model_name='violationperpetratororganization',
            name='value',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='organization.Organization'),
        ),
        migrations.DeleteModel(
            name='ViolationSource',
        ),
    ]
