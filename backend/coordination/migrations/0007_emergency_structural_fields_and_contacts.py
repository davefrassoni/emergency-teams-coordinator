from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("coordination", "0006_situation_visibility"),
    ]

    operations = [
        migrations.AddField(
            model_name="emergency",
            name="construction_type",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="emergency",
            name="damage_level",
            field=models.CharField(
                choices=[
                    ("UNKNOWN", "Not assessed"),
                    ("MINOR", "Minor visible damage"),
                    ("MODERATE", "Moderate damage"),
                    ("SEVERE", "Severe structural damage"),
                    ("COLLAPSE", "Partial or total collapse"),
                ],
                default="UNKNOWN",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="emergency",
            name="evidence_url",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="emergency",
            name="incident_type",
            field=models.CharField(
                choices=[
                    ("STRUCTURAL", "Structural damage"),
                    ("MEDICAL", "Medical emergency"),
                    ("FIRE", "Fire or hazardous materials"),
                    ("INFRASTRUCTURE", "Infrastructure or access"),
                    ("OTHER", "Other emergency"),
                ],
                default="OTHER",
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="EmergencyContact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=120)),
                ("phone", models.CharField(max_length=50)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("GENERAL", "General emergency"),
                            ("MEDICAL", "Medical"),
                            ("FIRE", "Fire department"),
                            ("CIVIL_PROTECTION", "Civil protection"),
                            ("OTHER", "Other"),
                        ],
                        default="GENERAL",
                        max_length=30,
                    ),
                ),
                ("notes", models.CharField(blank=True, max_length=240)),
                ("is_public", models.BooleanField(default=True)),
                ("priority", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "situation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="emergency_contacts",
                        to="coordination.situation",
                    ),
                ),
            ],
            options={"ordering": ["priority", "label"]},
        ),
    ]
