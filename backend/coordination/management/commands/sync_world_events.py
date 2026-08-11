import time

from django.core.management.base import BaseCommand

from coordination.world_events import sync_world_events


class Command(BaseCommand):
    help = "Synchronize global hazard events from GDACS, USGS, and NASA EONET."

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--interval", type=int, default=3600)

    def handle(self, *args, **options):
        interval = max(60, options["interval"])
        while True:
            results = sync_world_events()
            for name, result in results.items():
                if result.get("ok"):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{name}: created={result.get('created', 0)} "
                            f"updated={result.get('updated', 0)}"
                        )
                    )
                else:
                    self.stderr.write(f"{name}: {result.get('error')}")
            if not options["watch"]:
                break
            time.sleep(interval)
