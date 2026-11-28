"""
Phase 4 Test Suite for Sahaaya AI RAG Pipeline.
Comprehensive tests for DocumentLoader, TextExtractor, DocumentChunker, RAGIndexer,
DocumentRetriever, CitationBuilder, Security Path Guards, and REST API Endpoints.
"""

import sys
import unittest
import json
import tempfile
from pathlib import Path
import pypdf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from models import db
from rag.document_loader import DocumentLoader
from rag.text_extractor import TextExtractor
from rag.chunker import DocumentChunker
from rag.indexer import RAGIndexer
from rag.retriever import DocumentRetriever
from rag.citation import CitationBuilder
from scripts.generate_official_docs import generate_and_index_all, build_pdf_file


class TestPhase4RAGPipeline(unittest.TestCase):
    """Test suite for Phase 4 Government Document RAG Pipeline."""

    @classmethod
    def setUpClass(cls):
        """Set up in-memory app and initialize the RAG index and documents once."""
        cls.app = create_app("testing")
        with cls.app.app_context():
            db.create_all()
            generate_and_index_all()

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

    def tearDown(self):
        self.app_context.pop()

    # --- 1. PDF Text Extraction & Multi-Page Tests ---
    def test_01_pdf_text_extraction(self):
        """Test extraction of text from an official guideline PDF."""
        pdf_path = DocumentLoader.get_approved_directory() / "gruha_lakshmi_guidelines.pdf"
        self.assertTrue(pdf_path.exists())

        extraction = TextExtractor.extract_from_pdf(pdf_path)
        self.assertEqual(extraction["extraction_status"], "success")
        self.assertFalse(extraction["ocr_required"])
        self.assertEqual(extraction["page_count"], 2)
        self.assertGreater(extraction["total_characters"], 100)

        # Verify page 1 contains key government text
        page_1_text = extraction["pages"][0]["text"]
        self.assertIn("GOVERNMENT OF KARNATAKA", page_1_text)
        self.assertIn("2,000", page_1_text)

    def test_02_multipage_document_processing(self):
        """Test extraction and page preservation across multiple pages."""
        pdf_path = DocumentLoader.get_approved_directory() / "yuva_nidhi_guidelines.pdf"
        extraction = TextExtractor.extract_from_pdf(pdf_path)

        self.assertEqual(extraction["page_count"], 2)
        self.assertEqual(len(extraction["pages"]), 2)
        self.assertEqual(extraction["pages"][0]["page_number"], 1)
        self.assertEqual(extraction["pages"][1]["page_number"], 2)
        self.assertIn("3,000", extraction["pages"][0]["text"])
        self.assertIn("APPLICATION PROCESS", extraction["pages"][1]["text"])

    # --- 2. Page-Aware Chunking Tests ---
    def test_03_page_aware_chunking_and_metadata(self):
        """Test DocumentChunker splits pages into chunks while preserving page numbers and metadata."""
        chunker = DocumentChunker(chunk_size=500, chunk_overlap=80)
        doc_meta = {
            "doc_id": "test_doc_01",
            "scheme_slug": "test-scheme",
            "document_title": "Test Scheme Guidelines",
            "official_source_url": "https://gov.in/test",
            "verification_status": "Verified",
        }
        pages = [
            {"page_number": 1, "text": "Section 1: Introduction\n" + ("This is paragraph 1 of page 1. " * 25)},
            {"page_number": 2, "text": "Section 2: Benefits\n" + ("This is paragraph 1 of page 2. " * 25)},
        ]

        chunks = chunker.chunk_document(doc_meta, pages)
        self.assertGreaterEqual(len(chunks), 2)

        # Verify page number preservation
        page_1_chunks = [c for c in chunks if c["page_number"] == 1]
        page_2_chunks = [c for c in chunks if c["page_number"] == 2]
        self.assertGreater(len(page_1_chunks), 0)
        self.assertGreater(len(page_2_chunks), 0)

        for c in chunks:
            self.assertEqual(c["doc_id"], "test_doc_01")
            self.assertEqual(c["scheme_slug"], "test-scheme")
            self.assertEqual(c["official_source_url"], "https://gov.in/test")
            self.assertEqual(c["verification_status"], "Verified")

    # --- 3. Duplicate Detection & File Hashing ---
    def test_04_duplicate_detection_by_hash(self):
        """Test SHA-256 calculation identifies duplicate files accurately."""
        pdf_path = DocumentLoader.get_approved_directory() / "gruha_lakshmi_guidelines.pdf"
        hash_1 = DocumentLoader.calculate_file_hash(pdf_path)
        hash_2 = DocumentLoader.calculate_file_hash(pdf_path)
        self.assertEqual(hash_1, hash_2)
        self.assertEqual(len(hash_1), 64)

    # --- 4. FTS5 Indexing & BM25 Ranking Tests ---
    def test_05_fts5_indexing_and_bm25_retrieval(self):
        """Test FTS5 full-text indexing and BM25 search ranking."""
        retriever = DocumentRetriever()
        results = retriever.search(query="Gruha Lakshmi Rs 2000 DBT", top_k=5)

        self.assertEqual(results["query_status"], "success")
        self.assertGreater(results["total_results"], 0)
        self.assertIn("SQLite FTS5 BM25", results["system_description"])

        top_citation = results["citations"][0]
        self.assertEqual(top_citation["scheme_slug"], "gruha-lakshmi")
        self.assertEqual(top_citation["page_number"], 1)
        self.assertIn("Gruha Lakshmi", top_citation["document_title"])
        self.assertEqual(top_citation["verification_status"], "demo_only")
        self.assertIn("[DEMO ONLY - LOCALLY GENERATED MATERIAL]", top_citation["verification_badge"])
        self.assertFalse(top_citation["is_authentic_official_doc"])

    def test_06_scheme_specific_filtering(self):
        """Test filtering search results strictly by scheme_slug."""
        retriever = DocumentRetriever()

        # Search for 'Aadhaar' filtered by pm-kisan
        res_kisan = retriever.search(query="Aadhaar", scheme_slug="pm-kisan", top_k=5)
        self.assertEqual(res_kisan["query_status"], "success")
        for cit in res_kisan["citations"]:
            self.assertEqual(cit["scheme_slug"], "pm-kisan")

        # Search for 'Aadhaar' filtered by gruha-lakshmi
        res_gl = retriever.search(query="Aadhaar", scheme_slug="gruha-lakshmi", top_k=5)
        self.assertEqual(res_gl["query_status"], "success")
        for cit in res_gl["citations"]:
            self.assertEqual(cit["scheme_slug"], "gruha-lakshmi")

    # --- 5. Citation Generation Tests ---
    def test_07_citation_structure_and_formatting(self):
        """Test CitationBuilder constructs verifiable page and URL citations."""
        row_mock = {
            "document_title": "Official Gruha Jyothi Domestic Electricity Rules",
            "page_number": 1,
            "scheme_slug": "gruha-jyothi",
            "official_source_url": "https://sevasindhugs.karnataka.gov.in/gruhajyothi",
            "verification_status": "verified",
            "content": "Free electricity up to 200 units per month across all five ESCOMs.",
            "rank": -0.85,
        }
        citation = CitationBuilder.build_citation(row_mock, citation_number=1)

        self.assertEqual(citation["citation_id"], "CIT-01")
        self.assertEqual(citation["page_number"], 1)
        self.assertIn("Page 1", citation["formatted_citation"])
        self.assertIn("Official Portal", citation["formatted_citation"])
        self.assertEqual(citation["verification_status"], "verified")
        self.assertTrue(citation["is_authentic_official_doc"])
        self.assertIn("[VERIFIED OFFICIAL DOCUMENT]", citation["verification_badge"])
        self.assertIn("200 units", citation["passage_snippet"])

    # --- 6. Edge Cases: Empty Query & Insufficient Evidence ---
    def test_08_empty_query_handling(self):
        """Test empty and whitespace queries return safe empty_query status."""
        retriever = DocumentRetriever()
        res1 = retriever.search(query="")
        self.assertEqual(res1["query_status"], "empty_query")
        self.assertEqual(len(res1["citations"]), 0)

        res2 = retriever.search(query="   ")
        self.assertEqual(res2["query_status"], "empty_query")

    def test_09_insufficient_evidence_no_hallucinations(self):
        """Test that unanswerable queries return insufficient_evidence rather than fabricating answers."""
        retriever = DocumentRetriever()
        res = retriever.search(query="NonexistentRocket9999 QuantumFluxColonization8888")

        self.assertEqual(res["query_status"], "insufficient_evidence")
        self.assertEqual(res["total_results"], 0)
        self.assertEqual(len(res["citations"]), 0)
        self.assertIn("No reliable official source passage was found", res["message"])

    # --- 7. Scanned PDF / OCR Handling ---
    def test_10_scanned_pdf_requires_ocr_reporting(self):
        """Test that scanned PDFs without text trigger ocr_required status instead of silent empty indexing."""
        approved_dir = DocumentLoader.get_approved_directory()
        scanned_pdf_path = approved_dir / "test_scanned_mock.pdf"

        # Build blank page PDF simulating a scanned document without OCR
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=612, height=792)
        with open(scanned_pdf_path, "wb") as f:
            writer.write(f)

        try:
            extraction = TextExtractor.extract_from_pdf(scanned_pdf_path)
            self.assertTrue(extraction["ocr_required"])
            self.assertEqual(extraction["extraction_status"], "ocr_required")
            self.assertIn("Optical Character Recognition (OCR) is required", extraction["message"])
        finally:
            if scanned_pdf_path.exists():
                scanned_pdf_path.unlink()

    # --- 8. Unverified Document Handling ---
    def test_11_unverified_document_handling(self):
        """Test that documents flagged as Unverified preserve this status in citations."""
        approved_dir = DocumentLoader.get_approved_directory()
        unverified_pdf = approved_dir / "test_unverified_guideline.pdf"

        build_pdf_file(
            unverified_pdf,
            [["DRAFT CIRCULAR", "This is an unverified draft proposal for pilot testing."]]
        )

        try:
            extraction = TextExtractor.extract_from_pdf(unverified_pdf)
            chunker = DocumentChunker()
            doc_meta = {
                "doc_id": "doc_unverified_99",
                "document_title": "Unverified Pilot Draft",
                "scheme_slug": "pilot-draft",
                "official_source_url": "https://gov.in/draft",
                "verification_status": "Unverified",
                "file_hash": "unverified_hash_99",
                "page_count": 1,
            }
            chunks = chunker.chunk_document(doc_meta, extraction["pages"])
            indexer = RAGIndexer()
            indexer.index_document(doc_meta, chunks)

            retriever = DocumentRetriever()
            search_res = retriever.search(query="unverified draft proposal", scheme_slug="pilot-draft")
            self.assertEqual(search_res["query_status"], "success")
            self.assertEqual(search_res["citations"][0]["verification_status"], "unverified")
            self.assertIn("[UNVERIFIED SOURCE]", search_res["citations"][0]["formatted_citation"])
            self.assertFalse(search_res["citations"][0]["is_authentic_official_doc"])
        finally:
            if unverified_pdf.exists():
                unverified_pdf.unlink()
            indexer.remove_document("doc_unverified_99")

    # --- 9. Security Path Traversal Guard Tests ---
    def test_12_security_path_traversal_protection(self):
        """Test DocumentLoader rejects arbitrary file paths outside approved directory."""
        # Attempting path traversal with ../
        with self.assertRaises(PermissionError):
            DocumentLoader.validate_safe_path("../../../Windows/System32/cmd.exe")

        with self.assertRaises(PermissionError):
            DocumentLoader.validate_safe_path("C:/Windows/win.ini")

        # API Ingestion test for path traversal rejection
        res = self.client.post("/api/rag/ingest", json={
            "filename": "../../../Windows/win.ini",
            "metadata": {"document_title": "Malicious Traversal Attempt"}
        })
        self.assertEqual(res.status_code, 403)
        self.assertIn("Security Violation", res.get_json()["message"])

    # --- 10. API Endpoint Tests ---
    def test_13_api_rag_search(self):
        """Test POST /api/rag/search endpoint."""
        payload = {
            "query": "Gruha Lakshmi Rs 2000 monthly bank transfer",
            "scheme_slug": "gruha-lakshmi",
            "top_k": 3,
        }
        res = self.client.post("/api/rag/search", json=payload)
        self.assertEqual(res.status_code, 200)

        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["query_status"], "success")
        self.assertGreater(len(data["data"]["citations"]), 0)

    def test_14_api_rag_documents_list(self):
        """Test GET /api/rag/documents endpoint."""
        res = self.client.get("/api/rag/documents")
        self.assertEqual(res.status_code, 200)

        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertGreater(data["data"]["total_documents"], 0)
        self.assertGreater(data["data"]["total_chunks_indexed"], 0)

        doc_titles = [d["document_title"] for d in data["data"]["documents"]]
        self.assertTrue(any("Gruha Lakshmi" in t for t in doc_titles))

    # --- 11. Source Authenticity & Verification States ---
    def test_15_all_three_verification_states_and_badges(self):
        """Test that CitationBuilder correctly handles and distinguishes all 3 verification states."""
        # 1. Verified official document
        cit_verified = CitationBuilder.build_citation({
            "document_title": "Official Government Gazette Notification",
            "page_number": 3,
            "scheme_slug": "gruha-lakshmi",
            "official_source_url": "https://sevasindhu.karnataka.gov.in/",
            "verification_status": "verified",
            "content": "Authentic official gazette text.",
        }, citation_number=1)
        self.assertEqual(cit_verified["verification_status"], "verified")
        self.assertTrue(cit_verified["is_authentic_official_doc"])
        self.assertEqual(cit_verified["verification_badge"], "[VERIFIED OFFICIAL DOCUMENT]")
        self.assertIn("Official Portal", cit_verified["formatted_citation"])

        # 2. Demo only / locally generated demonstration excerpt
        cit_demo = CitationBuilder.build_citation({
            "document_title": "Gruha Lakshmi Operational Guidelines (Demonstration Excerpt)",
            "page_number": 1,
            "scheme_slug": "gruha-lakshmi",
            "official_source_url": "https://sevasindhu.karnataka.gov.in/",
            "verification_status": "demo_only",
            "content": "Demonstration excerpt of government order.",
        }, citation_number=2)
        self.assertEqual(cit_demo["verification_status"], "demo_only")
        self.assertFalse(cit_demo["is_authentic_official_doc"])
        self.assertEqual(cit_demo["verification_badge"], "[DEMO ONLY - LOCALLY GENERATED MATERIAL]")
        self.assertIn("Reference Portal", cit_demo["formatted_citation"])

        # 3. Unverified source
        cit_unverified = CitationBuilder.build_citation({
            "document_title": "Third-Party Scheme Summary",
            "page_number": 1,
            "scheme_slug": "gruha-lakshmi",
            "official_source_url": "https://external-blog.com/schemes",
            "verification_status": "unverified",
            "content": "Unverified summary information.",
        }, citation_number=3)
        self.assertEqual(cit_unverified["verification_status"], "unverified")
        self.assertFalse(cit_unverified["is_authentic_official_doc"])
        self.assertEqual(cit_unverified["verification_badge"], "[UNVERIFIED SOURCE]")
        self.assertIn("Unverified Portal", cit_unverified["formatted_citation"])


if __name__ == "__main__":
    unittest.main()
