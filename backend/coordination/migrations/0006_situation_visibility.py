from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("coordination", "0005_featurerequest_situation_codename_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="situation",
            name="is_public",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="situation",
            name="public_reporting_enabled",
            field=models.BooleanField(default=False),
        ),
    ]
