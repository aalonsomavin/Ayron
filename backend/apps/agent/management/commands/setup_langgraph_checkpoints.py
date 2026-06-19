from django.core.management.base import BaseCommand

from apps.agent.checkpoint import setup_checkpointer


class Command(BaseCommand):
    help = "Create LangGraph checkpoint tables in PostgreSQL"

    def handle(self, *args, **options):
        from apps.agent.checkpoint import _uses_sqlite, setup_checkpointer

        if _uses_sqlite():
            self.stdout.write("Skipping checkpoint setup for non-PostgreSQL database.")
            return
        setup_checkpointer()
        self.stdout.write(self.style.SUCCESS("LangGraph checkpoint tables are ready."))
