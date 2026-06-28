from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = 'api'
    verbose_name = 'Noya AI API'

    def ready(self):
        """Initialize RAG service eagerly when Django starts.

        This ensures the vector database and embedding model are loaded
        before the first user request, eliminating cold-start latency.
        """
        import os
        # Skip during management commands (migrate, collectstatic, etc.)
        if os.environ.get('RUN_MAIN') != 'true' and not os.environ.get('DJANGO_SETTINGS_MODULE'):
            return

        try:
            from .rag_service import get_rag_service
            rag = get_rag_service()
            if rag and rag.initialized:
                print(f"[RAG] Eager initialization complete. Collection count: {rag.collection.count() if rag.collection else 0}")
            else:
                print("[RAG] Eager initialization attempted but service not available (missing deps or data).")
        except Exception as e:
            print(f"[RAG] Eager initialization error (non-blocking): {e}")
