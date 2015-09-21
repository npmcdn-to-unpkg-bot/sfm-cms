# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_date_extensions.fields


class Migration(migrations.Migration):

    dependencies = [
        ('person', '0005_auto_20150921_1748'),
        ('organization', '0001_initial'),
        ('source', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Context',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('value', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='MembershipDate',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('value', django_date_extensions.fields.ApproximateDateField(max_length=10)),
                ('object_ref', models.ForeignKey(to='membership.Membership')),
            ],
        ),
        migrations.CreateModel(
            name='MembershipOrganization',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('lang', models.CharField(max_length=5, null=True)),
                ('object_ref', models.ForeignKey(to='membership.Membership')),
                ('sources', models.ManyToManyField(to='source.Source', related_name='membership_membershiporganization_related')),
                ('value', models.ForeignKey(to='organization.Organization')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MembershipPerson',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('lang', models.CharField(max_length=5, null=True)),
                ('object_ref', models.ForeignKey(to='membership.Membership')),
                ('sources', models.ManyToManyField(to='source.Source', related_name='membership_membershipperson_related')),
                ('value', models.ForeignKey(to='person.Person')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MembershipRank',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('lang', models.CharField(max_length=5, null=True)),
                ('object_ref', models.ForeignKey(to='membership.Membership')),
                ('sources', models.ManyToManyField(to='source.Source', related_name='membership_membershiprank_related')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MembershipRole',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('lang', models.CharField(max_length=5, null=True)),
                ('object_ref', models.ForeignKey(to='membership.Membership')),
                ('sources', models.ManyToManyField(to='source.Source', related_name='membership_membershiprole_related')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MembershipTitle',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('lang', models.CharField(max_length=5, null=True)),
                ('value', models.TextField(null=True, default=None, blank=True)),
                ('object_ref', models.ForeignKey(to='membership.Membership')),
                ('sources', models.ManyToManyField(to='source.Source', related_name='membership_membershiptitle_related')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Rank',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('value', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('value', models.TextField()),
            ],
        ),
        migrations.AddField(
            model_name='membershiprole',
            name='value',
            field=models.ForeignKey(to='membership.Role', blank=True, null=True, default=None),
        ),
        migrations.AddField(
            model_name='membershiprank',
            name='value',
            field=models.ForeignKey(to='membership.Rank', blank=True, null=True, default=None),
        ),
        migrations.AlterUniqueTogether(
            name='membershiptitle',
            unique_together=set([('object_ref', 'lang')]),
        ),
        migrations.AlterUniqueTogether(
            name='membershiprole',
            unique_together=set([('object_ref', 'lang')]),
        ),
        migrations.AlterUniqueTogether(
            name='membershiprank',
            unique_together=set([('object_ref', 'lang')]),
        ),
        migrations.AlterUniqueTogether(
            name='membershipperson',
            unique_together=set([('object_ref', 'lang')]),
        ),
        migrations.AlterUniqueTogether(
            name='membershiporganization',
            unique_together=set([('object_ref', 'lang')]),
        ),
    ]
