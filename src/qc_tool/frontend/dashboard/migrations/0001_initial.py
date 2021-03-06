# Generated by Django 2.0.4 on 2018-07-09 13:53

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Delivery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.CharField(max_length=500)),
                ('filepath', models.CharField(max_length=500)),
                ('product_ident', models.CharField(blank=True, max_length=64, null=True)),
                ('date_uploaded', models.DateTimeField(default=django.utils.timezone.now)),
                ('date_last_checked', models.DateTimeField(null=True)),
                ('date_submitted', models.DateTimeField(null=True)),
                ('last_wps_status', models.CharField(max_length=64)),
                ('last_job_uuid', models.CharField(max_length=32)),
                ('last_job_status', models.CharField(max_length=64)),
                ('empty_status_document', models.TextField()),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job_uuid', models.CharField(max_length=32)),
                ('product_ident', models.CharField(max_length=64, null=True)),
                ('start', models.DateTimeField(blank=True, null=True)),
                ('end', models.DateTimeField(blank=True, null=True)),
                ('wps_status', models.CharField(max_length=64)),
                ('status', models.CharField(max_length=64)),
                ('status_document_path', models.CharField(max_length=500)),
                ('filename', models.CharField(blank=True, max_length=500, null=True)),
                ('filepath', models.CharField(blank=True, max_length=500, null=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
