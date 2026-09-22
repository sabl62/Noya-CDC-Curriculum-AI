
import os
import json
import glob
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        PointStruct,
        VectorParams,
        PayloadSchemaType,
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


COLLECTION_NAME = "cdc_curriculum"
EMBEDDING_DIMENSION = 384  # paraphrase-multilingual-MiniLM-L12-v2


class RAGService:

    def __init__(self):
        self.initialized = False
        self.qdrant_client = None
        self._embedding_model = None
        self.curriculum_dir = None
        self._query_embedding_cache: Dict[str, List[float]] = {}
        self._cache_maxsize = 256
        self._initialize()

    def _get_embedding_model(self):
        if self._embedding_model is None:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise Exception("SentenceTransformers not available")
            self._embedding_model = SentenceTransformer(
                "paraphrase-multilingual-MiniLM-L12-v2"
            )
        return self._embedding_model

    def _initialize(self):
        """Initialize RAG components. Non-blocking: logs errors but does not crash."""
        if not all([QDRANT_AVAILABLE, PYPDF_AVAILABLE, SENTENCE_TRANSFORMERS_AVAILABLE]):
            print(
                "[RAG] Missing core dependencies (Qdrant, SentenceTransformers, or PyPDF). "
                "RAG will be unavailable."
            )
            return

        try:
            from django.conf import settings

            qdrant_url = getattr(settings, 'QDRANT_URL', 'http://localhost:6333')
            qdrant_api_key = getattr(settings, 'QDRANT_API_KEY', '')

            if qdrant_api_key:
                self.qdrant_client = QdrantClient(
                    url=qdrant_url,
                    api_key=qdrant_api_key,
                    timeout=60,
                )
            else:
                self.qdrant_client = QdrantClient(url=qdrant_url, timeout=60)

            # Create collection if it doesn't exist
            collections = [c.name for c in self.qdrant_client.get_collections().collections]
            if COLLECTION_NAME not in collections:
                self.qdrant_client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=EMBEDDING_DIMENSION,
                        distance=Distance.COSINE,
                    ),
                )
                print(f"[RAG] Created collection '{COLLECTION_NAME}'")

            # Create payload indexes for filtered fields
            for field in ["class", "subject", "page_no"]:
                try:
                    self.qdrant_client.create_payload_index(
                        collection_name=COLLECTION_NAME,
                        field_name=field,
                        field_schema=PayloadSchemaType.KEYWORD,
                    )
                except Exception:
                    pass  # Index already exists

            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.curriculum_dir = os.path.join(base_dir, "cdc_curriculum")

            self.initialized = True
            count = self.qdrant_client.count(collection_name=COLLECTION_NAME).count
            print(f"[RAG] Initialized. Indexed chunks: {count}")

        except Exception as e:
            print(f"[RAG] Initialization error (non-blocking): {e}")
            self.initialized = False

    def process_pdfs(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Process all CDC PDFs and create embeddings"""
        if not self.initialized:
            return {"status": "error", "message": "RAG not initialized"}

        if not force_rebuild:
            count = self.qdrant_client.count(collection_name=COLLECTION_NAME).count
            if count > 0:
                return {
                    "status": "already_indexed",
                    "count": count,
                    "message": "Curriculum already indexed",
                }

        curriculum_path = Path(self.curriculum_dir)
        if not curriculum_path.exists():
            return {
                "status": "error",
                "message": f"Directory not found: {self.curriculum_dir}",
            }

        processed = 0
        errors = []

        
        pdf_files = list(curriculum_path.rglob("*.pdf"))

        for pdf_path in pdf_files:
            try:
                
                class_name = pdf_path.parent.name
                subject = pdf_path.stem
                print(f"[RAG] Processing: {class_name}/{subject}")

                pages_data = self._extract_text_from_pdf(str(pdf_path))
                if not pages_data:
                    continue

                chunks = self._chunk_text(pages_data, subject, class_name)
                if chunks:
                    self._add_chunks_to_collection(chunks, class_name, subject)
                    processed += len(chunks)

            except Exception as e:
                errors.append(f"{pdf_path.name}: {str(e)}")

        return {
            "status": "success",
            "processed": processed,
            "errors": errors,
            "total_chunks": self.qdrant_client.count(collection_name=COLLECTION_NAME).count,
        }

    def _extract_text_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        pages_data = []
        try:
            reader = PdfReader(pdf_path)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    pages_data.append({"text": text, "page_no": i + 1})
            return pages_data
        except Exception as e:
            print(f"[RAG] Error extracting {pdf_path}: {e}")
            return []

    def _create_chunk_obj(
        self, text: str, subject: str, class_name: str, page_no: int
    ) -> Dict:
        return {
            "text": text,
            "metadata": {"subject": subject, "class": class_name, "page_no": page_no},
        }

    def _chunk_text(
        self,
        pages_data: List[Dict],
        subject: str,
        class_name: str,
        chunk_size: int = 600,
    ) -> List[Dict]:
        chunks = []
        for page in pages_data:
            text = page["text"]
            page_no = page["page_no"]
            sentences = text.split(". ")

            current_chunk = []
            current_length = 0

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                if current_length + len(sentence) > chunk_size and current_chunk:
                    chunks.append(
                        self._create_chunk_obj(
                            ". ".join(current_chunk), subject, class_name, page_no
                        )
                    )
                    current_chunk = [sentence]
                    current_length = len(sentence)
                else:
                    current_chunk.append(sentence)
                    current_length += len(sentence)

            if current_chunk:
                chunks.append(
                    self._create_chunk_obj(
                        ". ".join(current_chunk), subject, class_name, page_no
                    )
                )
        return chunks

    def _add_chunks_to_collection(
        self, chunks: List[Dict], class_name: str, subject: str
    ):
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self._get_embedding_model().encode(texts).tolist()

        points = []
        for i, chunk in enumerate(chunks):
            point_id = hash(f"{class_name}_{subject}_{i}") % (2**63)
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embeddings[i],
                    payload={
                        "text": chunk["text"],
                        "subject": chunk["metadata"]["subject"],
                        "class": chunk["metadata"]["class"],
                        "page_no": chunk["metadata"]["page_no"],
                    },
                )
            )

        batch_size = 100
        for start in range(0, len(points), batch_size):
            batch = points[start : start + batch_size]
            self.qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=batch,
            )

    def _get_cached_embedding(self, query: str) -> List[float]:
        """Return cached embedding or compute and cache it."""
        if query in self._query_embedding_cache:
            return self._query_embedding_cache[query]
        embedding = self._get_embedding_model().encode([query]).tolist()[0]
        if len(self._query_embedding_cache) >= self._cache_maxsize:
            # Evict oldest (simple FIFO)
            oldest = next(iter(self._query_embedding_cache))
            del self._query_embedding_cache[oldest]
        self._query_embedding_cache[query] = embedding
        return embedding

    def retrieve(
        self,
        query: str,
        grade: Optional[str] = None,
        subject: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict]:
        if not self.initialized or not self.qdrant_client:
            return []
        try:
            page_match = re.search(r"(?:page|p\.)\s*(\d+)", query.lower())
            target_page = int(page_match.group(1)) if page_match else None

            # Build Qdrant filter conditions
            must_conditions = []
            if grade:
                must_conditions.append(
                    FieldCondition(key="class", match=MatchValue(value=grade))
                )
            if subject:
                must_conditions.append(
                    FieldCondition(key="subject", match=MatchValue(value=subject))
                )
            if target_page:
                must_conditions.append(
                    FieldCondition(key="page_no", match=MatchValue(value=target_page))
                )

            query_filter = Filter(must=must_conditions) if must_conditions else None

            query_embedding = self._get_cached_embedding(query)
            results = self.qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_embedding,
                limit=top_k,
                query_filter=query_filter,
            )

            retrieved = []
            for hit in results.points:
                payload = hit.payload
                retrieved.append(
                    {
                        "text": payload.get("text", ""),
                        "class": payload.get("class", ""),
                        "subject": payload.get("subject", ""),
                        "page_no": payload.get("page_no", ""),
                    }
                )
            return retrieved
        except Exception as e:
            print(f"[RAG] Error retrieving: {e}")
            return []

    def get_context_for_query_with_source(
        self, query: str, grade: str = None, subject: str = None, max_length: int = 2000
    ) -> tuple:
        from .chapter_pdf_context import pdf_page_to_printed
        retrieved = self.retrieve(query, grade, subject)
        if not retrieved:
            return ("", "No source found")

        context_parts = ["CDC Curriculum Reference:\n"]
        source_parts = []
        for item in retrieved:
            printed_page = pdf_page_to_printed(item['subject'], item['page_no'])
            context_parts.append(
                f"[Class {item['class']}, Page {printed_page}]: {item['text'][:500]}"
            )
            subject_name = str(item['subject']).title()
            if subject_name.lower() == 'omaths':
                subject_name = 'Optional Mathematics'
            source_parts.append(f"{subject_name} Page {printed_page}")

        context = "\n\n".join(context_parts)
        if len(context) > max_length:
            context = context[:max_length] + "..."

        return (context, ", ".join(list(set(source_parts))))

    def get_status(self) -> Dict[str, Any]:
        count = 0
        if self.qdrant_client:
            try:
                count = self.qdrant_client.count(collection_name=COLLECTION_NAME).count
            except Exception:
                pass
        return {
            "initialized": self.initialized,
            "total_chunks": count,
            "curriculum_dir": self.curriculum_dir,
        }

    def system_check(self) -> Dict[str, List[str]]:
        issues = []
        warnings = []

        if not QDRANT_AVAILABLE:
            issues.append("Qdrant client is not installed")
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            issues.append("SentenceTransformers is not installed")
        if not PYPDF_AVAILABLE:
            issues.append("PyPDF is not installed")
        if not self.initialized:
            issues.append("RAG service is not initialized")
        if self.curriculum_dir and not Path(self.curriculum_dir).exists():
            issues.append(f"Curriculum directory not found: {self.curriculum_dir}")
        if self.qdrant_client:
            try:
                count = self.qdrant_client.count(collection_name=COLLECTION_NAME).count
                if count == 0:
                    warnings.append("Curriculum collection has no indexed chunks")
            except Exception:
                warnings.append("Could not check collection count")

        return {"issues": issues, "warnings": warnings}


# Singleton instance setup
_rag_service = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


def initialize_rag(force_rebuild: bool = False) -> Dict[str, Any]:
    rag = get_rag_service()
    return rag.process_pdfs(force_rebuild=force_rebuild)
