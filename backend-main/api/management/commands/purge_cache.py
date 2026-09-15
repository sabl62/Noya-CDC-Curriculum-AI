"""Purge Noya's answer caches for a fresh start.

Clears, by default:
  - In-memory LRU (hot answers)
  - SemanticAnswerCache (learned AI answers, DB)
  - KnowledgeBaseEntry (precomputed textbook answers, DB)

Options:
  --events      Also clear the CacheLookupEvent audit trail
  --memory-only Only clear the in-memory LRU (no DB writes)
  --keep-kb     Keep KnowledgeBaseEntry rows (precomputed content)
"""

from django.core.management.base import BaseCommand

from api.models import CacheLookupEvent, KnowledgeBaseEntry, SemanticAnswerCache
from api.semantic_cache import get_semantic_cache_service


class Command(BaseCommand):
    help = "Purge semantic cache tiers (memory LRU, SemanticAnswerCache, KnowledgeBaseEntry)."

    def add_arguments(self, parser):
        parser.add_argument("--events", action="store_true", help="Also clear CacheLookupEvent audit log")
        parser.add_argument("--memory-only", action="store_true", help="Only clear the in-memory LRU")
        parser.add_argument("--keep-kb", action="store_true", help="Keep KnowledgeBaseEntry rows")

    def handle(self, *args, **options):
        cache = get_semantic_cache_service()

        cache.clear()
        self.stdout.write(self.style.SUCCESS("In-memory LRU cleared (512-entry hot cache)."))

        if options["memory_only"]:
            return

        semantic_deleted, _ = SemanticAnswerCache.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"SemanticAnswerCache: {semantic_deleted} entries deleted."))

        if not options["keep_kb"]:
            kb_deleted, _ = KnowledgeBaseEntry.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f"KnowledgeBaseEntry: {kb_deleted} entries deleted."))
        else:
            self.stdout.write("KnowledgeBaseEntry kept (--keep-kb).")

        if options["events"]:
            event_deleted, _ = CacheLookupEvent.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f"CacheLookupEvent: {event_deleted} events deleted."))

        self.stdout.write(self.style.SUCCESS("All requested cache tiers purged. Cache will re-learn from live AI answers."))
