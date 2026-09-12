import json

from django.core.management.base import BaseCommand

from api.rag_service import get_rag_service, initialize_rag


class Command(BaseCommand):
    help = "Initialize RAG service and index CDC curriculum PDFs into Qdrant."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-rebuild",
            action="store_true",
            help="Re-index all PDFs even if collection already has data.",
        )
        parser.add_argument(
            "--status",
            action="store_true",
            help="Show current RAG status without indexing.",
        )

    def handle(self, *args, **options):
        if options["status"]:
            rag = get_rag_service()
            status = rag.get_status()
            self.stdout.write(json.dumps(status, indent=2))
            return

        self.stdout.write("Initializing RAG service...")
        result = initialize_rag(force_rebuild=options["force_rebuild"])
        self.stdout.write(json.dumps(result, indent=2))

        if result.get("status") == "success":
            self.stdout.write(self.style.SUCCESS("RAG indexing complete."))
        elif result.get("status") == "already_indexed":
            self.stdout.write(self.style.WARNING("Collection already indexed. Use --force-rebuild to re-index."))
        elif result.get("status") == "error":
            self.stdout.write(self.style.ERROR(f"Error: {result.get('message')}"))
