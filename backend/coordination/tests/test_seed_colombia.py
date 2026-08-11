from django.core.management import call_command
from django.test import TestCase

from coordination.models import Emergency, Situation


class SeedColombiaEarthquakeTests(TestCase):
    def test_creates_public_operation_with_sourced_reports(self):
        call_command("seed_colombia_earthquake")

        situation = Situation.objects.get(codename="colombia")
        self.assertTrue(situation.is_public)
        self.assertTrue(situation.public_reporting_enabled)

        reports = Emergency.objects.filter(situation=situation)
        self.assertGreaterEqual(reports.count(), 5)
        for report in reports:
            self.assertEqual(report.source, Emergency.Source.EXTERNAL_FEED)
            self.assertTrue(report.evidence_url)
            self.assertIsNotNone(report.latitude)
            self.assertIsNotNone(report.longitude)

    def test_is_idempotent(self):
        call_command("seed_colombia_earthquake")
        first_count = Emergency.objects.filter(situation__codename="colombia").count()

        call_command("seed_colombia_earthquake")
        second_count = Emergency.objects.filter(situation__codename="colombia").count()

        self.assertEqual(first_count, second_count)
        self.assertEqual(Situation.objects.filter(codename="colombia").count(), 1)
