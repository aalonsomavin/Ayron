from django.conf import settings
from django.core.management.base import BaseCommand

from demo_data.mexar_pharma.seed import seed_mexar_demo


class Command(BaseCommand):
    help = "Seed the Mexar Pharma demo database (DEMO_DB_URL)"

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

        result = seed_mexar_demo(url, force=options["force"])
        if result.get("skipped"):
            self.stdout.write("Mexar demo database already seeded (use --force to re-seed).")
            return

        if result.get("schema_applied"):
            self.stdout.write("Applied Mexar demo schema.")

        self.stdout.write(
            self.style.SUCCESS(
                "Mexar demo seeded: "
                f"{result['productos']} productos, "
                f"{result['instituciones']} instituciones, "
                f"{result['pedidos']} pedidos, "
                f"{result['lineas']} líneas, "
                f"{result['cuentas']} cuentas CRM."
            )
        )
