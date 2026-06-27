from django.core.management.base import BaseCommand, CommandError

from coordination.models import FeedSource, Situation


class Command(BaseCommand):
    help = "Register the discovered Venezuela missing-person source."

    def add_arguments(self, parser):
        parser.add_argument("--codename", default="venezuela")
        parser.add_argument("--enable", action="store_true")

    def handle(self, *args, **options):
        try:
            situation = Situation.objects.get(codename=options["codename"])
        except Situation.DoesNotExist as exc:
            raise CommandError("Create the operation before seeding its feed.") from exc
        source, created = FeedSource.objects.update_or_create(
            situation=situation,
            source_url="https://desaparecidosterremotovenezuela.com/",
            defaults={
                "name": "Desaparecidos Terremoto Venezuela",
                "api_url": "https://desaparecidos-terremoto-api.theempire.tech/api",
                "adapter": FeedSource.Adapter.VENEZUELA_MISSING,
                "enabled": options["enable"],
                "last_error": (
                    ""
                    if options["enable"]
                    else "Pending source authorization: the people API requires reCAPTCHA for reads."
                ),
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} source {source.pk}; "
                f"enabled={source.enabled}"
            )
        )

