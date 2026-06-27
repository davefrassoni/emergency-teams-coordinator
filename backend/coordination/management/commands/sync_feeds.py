import time

from django.core.management.base import BaseCommand

from coordination.feed_ingestion import sync_source
from coordination.models import FeedSource


class Command(BaseCommand):
    help = "Synchronize enabled external emergency data feeds."

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--interval", type=int, default=900)

    def handle(self, *args, **options):
        interval = max(60, options["interval"])
        while True:
            sources = list(
                FeedSource.objects.filter(enabled=True).select_related("situation")
            )
            for source in sources:
                try:
                    result = sync_source(source)
                    self.stdout.write(
                        self.style.SUCCESS(f"{source.name}: {result}")
                    )
                except Exception as exc:
                    self.stderr.write(f"{source.name}: {exc}")
            if not options["watch"]:
                break
            time.sleep(interval)

