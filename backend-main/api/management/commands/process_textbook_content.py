import json

from django.core.management.base import BaseCommand, CommandError

from api.content_processor import (
    CONTENT_PROCESSOR_SYSTEM_PROMPT,
    build_content_processor_prompt,
    build_entries_from_processed_payload,
    extract_json_object,
    normalize_processed_payload,
    save_processed_entries,
)


class Command(BaseCommand):
    help = "Process one textbook content JSON file into KnowledgeBaseEntry records."

    def add_arguments(self, parser):
        parser.add_argument("input_json", help="Path to a JSON file with subject, grade, chapter, topic, raw_textbook_content.")
        parser.add_argument("--dry-run", action="store_true", help="Process and print summary without saving entries.")

    def handle(self, *args, **options):
        input_path = options["input_json"]
        try:
            with open(input_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except OSError as exc:
            raise CommandError(f"Could not read input file: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f"Input file is not valid JSON: {exc}") from exc

        required = ["subject", "grade", "chapter", "topic", "raw_textbook_content"]
        missing = [key for key in required if not str(payload.get(key, "")).strip()]
        if missing:
            raise CommandError(f"Missing required fields: {', '.join(missing)}")

        from api.ai_service import AIService

        service = AIService()
        prompt = build_content_processor_prompt(
            payload["subject"],
            payload["grade"],
            payload["chapter"],
            payload["topic"],
            payload["raw_textbook_content"],
        )
        raw_response = service._generate_with_fallbacks(prompt, CONTENT_PROCESSOR_SYSTEM_PROMPT)
        processed = normalize_processed_payload(extract_json_object(raw_response), payload)
        entries = build_entries_from_processed_payload(processed, payload)

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"Dry run: generated {len(entries)} entries."))
            self.stdout.write(json.dumps(processed, ensure_ascii=False, indent=2))
            return

        saved_count, saved_ids = save_processed_entries(entries)
        self.stdout.write(self.style.SUCCESS(f"Saved {saved_count} KnowledgeBaseEntry records: {saved_ids}"))
