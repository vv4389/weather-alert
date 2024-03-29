# Generated by Django 5.0.2 on 2024-02-14 17:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersubscription',
            name='subscription_arn',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='usersubscription',
            name='email',
            field=models.EmailField(max_length=254),
        ),
    ]
