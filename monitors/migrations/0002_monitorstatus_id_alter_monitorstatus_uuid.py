# Generated by Django 5.2.1 on 2025-05-14 10:48

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitors', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='monitorstatus',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='monitorstatus',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
