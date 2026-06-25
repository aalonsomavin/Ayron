from django.conf import settings
from django.core.management.base import BaseCommand

from demo_data.yivtol_agro.seed import seed_yivtol_demo


class Command(BaseCommand):
    help = "Seed the YIVTOL AyronOne demo database (DEMO_DB_URL)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Truncate and re-seed even if data already exists",
        )

    def handle(self, *args, **options):
        url = settings.DEMO_DB_URL
        if not url:
            self.stderr.write(self.style.ERROR("DEMO_DB_URL is not configured"))
            return

        result = seed_yivtol_demo(url, force=options["force"])
        if result.get("skipped"):
            self.stdout.write("YIVTOL demo database already seeded (use --force to re-seed).")
            return

        if result.get("schema_applied"):
            self.stdout.write("Applied YIVTOL demo schema.")

        self.stdout.write(
            self.style.SUCCESS(
                "YIVTOL demo seeded: "
                f"{result['vuelos']} vuelos, "
                f"{result['lotes']} lotes, "
                f"{result['mediciones']} mediciones agrícolas, "
                f"{result['corrales']} corrales, "
                f"{result['animales']} animales, "
                f"{result['alertas_agricola']} alertas agrícolas, "
                f"{result['alertas_ganaderia']} alertas ganaderas."
            )
        )
