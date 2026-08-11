from django.core.management.base import BaseCommand

from coordination.models import Emergency, Situation


SOURCE_NOTE = (
    "Figures are still being verified by authorities and may change. "
    "Not a substitute for official guidance — see the source link for the latest."
)

SEED_EMERGENCIES = [
    {
        "title": "M7.4 earthquake — Chocó epicenter",
        "location": "Near San José del Palmar, Chocó",
        "latitude": "4.843600",
        "longitude": "-76.242200",
        "incident_type": Emergency.IncidentType.OTHER,
        "damage_level": Emergency.DamageLevel.UNKNOWN,
        "people_affected": 0,
        "details": (
            "Magnitude 7.4 earthquake, depth ~107 km, struck 10 Aug 2026 07:34 local time "
            "near San José del Palmar. A magnitude 4.8 aftershock followed about an hour later. "
            f"Source: USGS / GDACS. {SOURCE_NOTE}"
        ),
        "evidence_url": "https://earthquake.usgs.gov/earthquakes/eventpage/us6000tjl2/executive",
    },
    {
        "title": "Building collapses reported",
        "location": "Cali, Valle del Cauca",
        "latitude": "3.451600",
        "longitude": "-76.532000",
        "incident_type": Emergency.IncidentType.STRUCTURAL,
        "damage_level": Emergency.DamageLevel.SEVERE,
        "people_affected": 0,
        "details": (
            "Press reports describe severe structural damage in Cali following the earthquake, "
            f"part of a nationwide toll of 61 collapsed buildings and 1,575 homes damaged. {SOURCE_NOTE}"
        ),
        "evidence_url": "https://www.cbsnews.com/news/colombia-earthquake-western-region-evacuations/",
    },
    {
        "title": "Structural damage and injuries reported",
        "location": "Manizales, Caldas",
        "latitude": "5.070300",
        "longitude": "-75.513800",
        "incident_type": Emergency.IncidentType.STRUCTURAL,
        "damage_level": Emergency.DamageLevel.SEVERE,
        "people_affected": 0,
        "details": (
            f"Heavy structural damage and injuries reported in Manizales. {SOURCE_NOTE}"
        ),
        "evidence_url": "https://abcnews.go.com/International/colombia-earthquake-fatalities-buildings-collapsed/story?id=135518897",
    },
    {
        "title": "Injuries and building damage reported",
        "location": "Quibdó, Chocó",
        "latitude": "5.694700",
        "longitude": "-76.661200",
        "incident_type": Emergency.IncidentType.STRUCTURAL,
        "damage_level": Emergency.DamageLevel.MODERATE,
        "people_affected": 0,
        "details": (
            f"Injuries and building damage reported in Quibdó, the department capital. {SOURCE_NOTE}"
        ),
        "evidence_url": "https://www.univision.com/noticias/america-latina/fuerte-sismo-sacude-el-departamento-de-choco-en-colombia-este-lunes",
    },
    {
        "title": "Partial terminal collapse — Matecaña International Airport",
        "location": "Pereira, Risaralda",
        "latitude": "4.812800",
        "longitude": "-75.739500",
        "incident_type": Emergency.IncidentType.STRUCTURAL,
        "damage_level": Emergency.DamageLevel.SEVERE,
        "construction_type": "Airport terminal",
        "people_affected": 0,
        "details": (
            f"Press reports describe a partial collapse of the Matecaña International Airport terminal. {SOURCE_NOTE}"
        ),
        "evidence_url": "https://abcnews.go.com/International/colombia-earthquake-fatalities-buildings-collapsed/story?id=135518897",
    },
    {
        "title": "Roughly 400 homes affected, ~20 structures collapsed",
        "location": "San José del Palmar, Chocó",
        "latitude": "4.975800",
        "longitude": "-76.239400",
        "incident_type": Emergency.IncidentType.STRUCTURAL,
        "damage_level": Emergency.DamageLevel.COLLAPSE,
        "people_affected": 0,
        "details": (
            "Preliminary local reports cite roughly 400 homes affected and about 20 structures "
            f"fully collapsed at the epicenter town; no fatalities confirmed there as of the initial reports. {SOURCE_NOTE}"
        ),
        "evidence_url": "https://occidente.co/colombia/terremoto-en-san-jose-del-palmar-epicentro-choco-danos/",
    },
]


class Command(BaseCommand):
    help = (
        "Create (or update) the public Colombia earthquake response operation and seed it "
        "with a handful of sourced, cited situation reports drawn from wire-service and local "
        "press coverage of the 10 Aug 2026 M7.4 Chocó earthquake."
    )

    def add_arguments(self, parser):
        parser.add_argument("--codename", default="colombia")

    def handle(self, *args, **options):
        situation, created = Situation.objects.update_or_create(
            codename=options["codename"],
            defaults={
                "name": "Colombia Earthquake Response",
                "location": "Chocó & western Colombia",
                "description": (
                    "Coordination space for the M7.4 earthquake that struck near San José del "
                    "Palmar, Chocó on 10 Aug 2026, with reported damage across Cali, Manizales, "
                    "Pereira, Quibdó and Armenia. Situation reports below are seeded from public "
                    "wire-service and local press coverage, each cited with a source link — "
                    "verify before acting. Community reports can be added from the public map."
                ),
                "status": Situation.Status.ACTIVE,
                "is_public": True,
                "public_reporting_enabled": True,
            },
        )
        created_count = 0
        updated_count = 0
        for entry in SEED_EMERGENCIES:
            _, was_created = Emergency.objects.update_or_create(
                situation=situation,
                title=entry["title"],
                location=entry["location"],
                defaults={
                    "latitude": entry["latitude"],
                    "longitude": entry["longitude"],
                    "triage": Emergency.Triage.UNKNOWN,
                    "status": Emergency.Status.VERIFIED,
                    "source": Emergency.Source.EXTERNAL_FEED,
                    "incident_type": entry["incident_type"],
                    "damage_level": entry["damage_level"],
                    "construction_type": entry.get("construction_type", ""),
                    "evidence_url": entry["evidence_url"],
                    "people_affected": entry["people_affected"],
                    "details": entry["details"],
                },
            )
            if was_created:
                created_count += 1
            else:
                updated_count += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} operation '{situation.codename}'; "
                f"situation reports: {created_count} created, {updated_count} updated"
            )
        )
