# Generated by Django 2.1.7 on 2019-02-21 16:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0006_auto_20190221_1617'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='delivery',
            name='date_last_checked',
        ),
        migrations.RemoveField(
            model_name='delivery',
            name='last_wps_status',
        ),
    ]