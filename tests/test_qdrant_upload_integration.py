from __future__ import annotations

from pathlib import Path
import unittest
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models

from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.indexing import IndexingOrchestrator, IndexingRequest
from receipt_ai.features.extraction.models import ExtractionRequest
from receipt_ai.features.extraction.orchestrator import run_upload_extraction


class QdrantUploadIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_sample_pdf_upload_indexes_points_in_qdrant(self):
        root = Path(__file__).resolve().parents[1]
        sample_pdf = root / "Official Receipt from April 18 - 22.pdf"
        if not sample_pdf.exists():
            self.skipTest(f"Sample PDF not found: {sample_pdf}")

        config = ExtractionConfig.from_env()
        if not config.qdrant_url.strip():
            self.skipTest("QDRANT_URL is missing.")

        client = QdrantClient(
            url=config.qdrant_url.strip(),
            api_key=(config.qdrant_api_key or None),
        )
        try:
            client.get_collections()
        except Exception as exc:
            self.skipTest(f"Qdrant unavailable: {exc}")

        file_key = f"IntegrationTests/{sample_pdf.stem}-{uuid.uuid4().hex}"
        folder = "IntegrationTests"

        # Always cleanup this test document key from Qdrant.
        def _cleanup_qdrant() -> None:
            try:
                client.delete(
                    collection_name=config.qdrant_collection,
                    points_selector=models.FilterSelector(
                        filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="metadata.document_key",
                                    match=models.MatchValue(value=file_key),
                                )
                            ]
                        )
                    ),
                )
            except Exception:
                pass

        self.addCleanup(_cleanup_qdrant)

        extraction = await run_upload_extraction(
            ExtractionRequest(
                filename=sample_pdf.name,
                content_type="application/pdf",
                file_bytes=sample_pdf.read_bytes(),
                storage_folder=folder,
            )
        )
        self.assertEqual(
            extraction.status,
            "success",
            msg=f"Extraction failed: {extraction.error or 'unknown error'}",
        )
        self.assertTrue(extraction.text.strip(), msg="Extraction returned empty text.")

        orchestrator = IndexingOrchestrator(config)
        output_path = orchestrator.process(
            IndexingRequest(
                file_key=file_key,
                folder=folder,
                filename=sample_pdf.name,
                extracted_text=extraction.text,
                doc_type="pdf",
            )
        )
        self.assertTrue(output_path, msg="Indexing did not return chunk output path.")

        points, _ = client.scroll(
            collection_name=config.qdrant_collection,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.document_key",
                        match=models.MatchValue(value=file_key),
                    )
                ]
            ),
            limit=10,
            with_payload=True,
            with_vectors=False,
        )
        self.assertGreater(
            len(points),
            0,
            msg="No Qdrant points found for uploaded PDF document key.",
        )


if __name__ == "__main__":
    unittest.main()
