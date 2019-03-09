# Generated by Django 2.1.7 on 2019-03-09 07:04

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('mainsite', '0006_book_show'),
    ]

    operations = [
        migrations.AddField(
            model_name='volume',
            name='edited_data',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, verbose_name='此卷被编辑过的时间（格式转换后也算编辑）'),
        ),
    ]
