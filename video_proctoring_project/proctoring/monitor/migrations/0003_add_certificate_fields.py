# Generated migration file for certificate feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0002_session_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='session',
            name='exam_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='session',
            name='exam_score',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='session',
            name='total_questions',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='session',
            name='correct_answers',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='session',
            name='certificate_generated',
            field=models.BooleanField(default=False),
        ),
    ]
