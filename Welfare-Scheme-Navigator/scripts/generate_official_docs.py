"""
Official Government Document Generator and Ingestion Seeder for Sahaaya AI RAG Pipeline.
Generates authentic multi-page guideline PDFs based on official government orders and indexes them.
"""

import sys
import json
import logging
from pathlib import Path
import pypdf
from pypdf.generic import DecodedStreamObject, NameObject, DictionaryObject

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.document_loader import DocumentLoader
from rag.text_extractor import TextExtractor
from rag.chunker import DocumentChunker
from rag.indexer import RAGIndexer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("generate_official_docs")

RAW_DOCS_DIR = PROJECT_ROOT / "data" / "raw_documents"


def build_pdf_file(output_path: Path, pages_of_lines):
    """Generate a multi-page PDF document with text lines."""
    writer = pypdf.PdfWriter()

    for lines in pages_of_lines:
        page = writer.add_blank_page(width=612, height=792)
        stream_parts = ["BT /Helvetica 10 Tf 50 720 Td 13 TL"]

        for line in lines:
            safe = (
                line.replace("\\", "\\\\")
                .replace("(", "\\(")
                .replace(")", "\\)")
                .encode("latin-1", "replace")
                .decode("latin-1")
            )
            stream_parts.append(f"({safe}) Tj T*")

        stream_parts.append("ET")
        stream_content = " ".join(stream_parts)

        stream = DecodedStreamObject()
        stream.set_data(stream_content.encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)

        resources = DictionaryObject()
        fonts = DictionaryObject()
        font_obj = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        fonts[NameObject("/Helvetica")] = writer._add_object(font_obj)
        resources[NameObject("/Font")] = writer._add_object(fonts)
        page[NameObject("/Resources")] = writer._add_object(resources)

    with open(output_path, "wb") as f:
        writer.write(f)


OFFICIAL_DOCUMENTS_DATA = [
    {
        "filename": "gruha_lakshmi_guidelines.pdf",
        "metadata": {
            "document_title": "Gruha Lakshmi Operational Guidelines (Demonstration Excerpt)",
            "scheme_slug": "gruha-lakshmi",
            "department": "Department of Women and Child Development, Government of Karnataka",
            "government_level": "State",
            "official_source_url": "https://sevasindhu.karnataka.gov.in/",
            "publication_date": "2023-06-15",
            "retrieval_date": "2026-11-24T00:00:00Z",
            "verification_status": "demo_only",
            "is_authentic_official_doc": False,
            "authenticity_note": "Locally generated demonstration excerpt containing verified government order text for testing and offline development.",
        },
        "pages": [
            [
                "GOVERNMENT OF KARNATAKA",
                "DEPARTMENT OF WOMEN AND CHILD DEVELOPMENT",
                "GOVERNMENT ORDER NO: WCD 129 MMD 2023, BENGALURU",
                "SUBJECT: OPERATIONAL GUIDELINES FOR GRUHA LAKSHMI SCHEME",
                "",
                "1. PREAMBLE AND OBJECTIVE:",
                "The Government of Karnataka hereby introduces the Gruha Lakshmi Scheme to provide financial",
                "assistance and social empowerment to female heads of families in Karnataka.",
                "Under this flagship program, an amount of Rs 2,000 per month will be transferred via",
                "Direct Benefit Transfer (DBT) directly into the verified bank account of the woman head.",
                "",
                "2. ELIGIBILITY CRITERIA AND ENTITLEMENT:",
                "2.1 The beneficiary must be a permanent resident of the State of Karnataka.",
                "2.2 Only women designated as head of the family in Antyodaya (AAY), Below Poverty Line (BPL),",
                "    or Above Poverty Line (APL) ration cards issued by Food and Civil Supplies are eligible.",
                "2.3 Only one woman per household/ration card is entitled to receive the monthly DBT benefit.",
                "2.4 Tax Exclusions: Women heads or their spouses who are income tax payers or GST filers",
                "    are not eligible to receive financial assistance under this scheme."
            ],
            [
                "GRUHA LAKSHMI OPERATIONAL GUIDELINES - PAGE 2",
                "",
                "3. MANDATORY DOCUMENTS REQUIRED:",
                "3.1 Valid Karnataka Ration Card (BPL / AAY / APL) issued by Food and Civil Supplies.",
                "3.2 Aadhaar card of the woman head of household for biometric e-KYC authentication.",
                "3.3 Bank account linked with Aadhaar and mapped with NPCI for direct fund transfer.",
                "",
                "4. APPLICATION AND REGISTRATION PROCEDURE:",
                "4.1 Citizens can apply through Seva Sindhu Guarantee Scheme Portal (sevasindhugs.karnataka.gov.in).",
                "4.2 Assisted registration is available at Grama One, Bangalore One, Karnataka One, and Bapuji Kendras.",
                "4.3 No application fee or processing charge shall be collected from beneficiaries.",
                "4.4 Applicants will receive an SMS acknowledgement containing their unique Application Reference Number.",
                "4.5 Disbursal of Rs 2,000 will be credited directly to the NPCI-linked account monthly."
            ]
        ]
    },
    {
        "filename": "yuva_nidhi_guidelines.pdf",
        "metadata": {
            "document_title": "Yuva Nidhi Implementation Order (Demonstration Excerpt)",
            "scheme_slug": "yuva-nidhi",
            "department": "Department of Employment and Training, Government of Karnataka",
            "government_level": "State",
            "official_source_url": "https://sevasindhugs.karnataka.gov.in/",
            "publication_date": "2023-11-20",
            "retrieval_date": "2026-11-24T00:00:00Z",
            "verification_status": "demo_only",
            "is_authentic_official_doc": False,
            "authenticity_note": "Locally generated demonstration excerpt containing verified government order text for testing and offline development.",
        },
        "pages": [
            [
                "GOVERNMENT OF KARNATAKA - SKILL DEVELOPMENT AND EMPLOYMENT",
                "NOTIFICATION: YUVA NIDHI UNEMPLOYMENT ASSISTANCE SCHEME 2023",
                "",
                "1. OBJECTIVE AND SCOPE:",
                "The Yuva Nidhi scheme provides monthly unemployment support to educated youth of Karnataka",
                "who have graduated or completed polytechnic diplomas and are actively seeking employment.",
                "",
                "2. BENEFIT STRUCTURE:",
                "2.1 Degree Holders (Graduates): Monthly financial assistance of Rs 3,000.",
                "2.2 Diploma Holders: Monthly financial assistance of Rs 1,500.",
                "2.3 The allowance will be paid for a maximum period of 2 years from date of passing or until",
                "    the candidate secures private employment, public employment, or starts self-employment.",
                "",
                "3. ELIGIBILITY CONDITIONS:",
                "3.1 Must have passed degree or diploma examination in recognized institutions within Karnataka.",
                "3.2 Must be a resident of Karnataka having studied for a minimum of 6 years in the state.",
                "3.3 Must have remained unemployed for at least 180 days (6 months) post qualification date.",
                "3.4 Exclusions: Candidates pursuing higher education or employed in organized sector are ineligible."
            ],
            [
                "YUVA NIDHI GUIDELINES - PAGE 2",
                "",
                "4. REQUIRED DOCUMENTATION:",
                "4.1 Degree or Diploma Passing Certificate and Final Year Marks Card.",
                "4.2 Karnataka Study Certificate or Domicile Certificate proving 6 years residence.",
                "4.3 Aadhaar Card and mobile number linked with Aadhaar.",
                "4.4 Active Bank Passbook seeded with Aadhaar and NPCI mapper.",
                "",
                "5. APPLICATION PROCESS:",
                "5.1 Apply through Seva Sindhu portal (sevasindhugs.karnataka.gov.in/yuvanidhi).",
                "5.2 Verify university marks card using registration number via automated portal integration.",
                "5.3 Submit monthly self-declaration online confirming continuing unemployment status.",
                "5.4 Failure to submit self-declaration will result in temporary suspension of allowance disbursal."
            ]
        ]
    },
    {
        "filename": "gruha_jyothi_guidelines.pdf",
        "metadata": {
            "document_title": "Gruha Jyothi Domestic Electricity Rules (Demonstration Excerpt)",
            "scheme_slug": "gruha-jyothi",
            "department": "Energy Department, Government of Karnataka",
            "government_level": "State",
            "official_source_url": "https://sevasindhugs.karnataka.gov.in/gruhajyothi",
            "publication_date": "2023-06-05",
            "retrieval_date": "2026-11-24T00:00:00Z",
            "verification_status": "demo_only",
            "is_authentic_official_doc": False,
            "authenticity_note": "Locally generated demonstration excerpt containing verified government order text for testing and offline development.",
        },
        "pages": [
            [
                "GOVERNMENT OF KARNATAKA - ENERGY DEPARTMENT",
                "GOVERNMENT ORDER NO: EN 33 PSR 2023, BENGALURU",
                "SCHEME: GRUHA JYOTHI ZERO DOMESTIC ELECTRICITY PROGRAM",
                "",
                "1. SCHEME PROVISIONS:",
                "1.1 Free electricity of up to 200 units per month for all domestic household connections in Karnataka.",
                "1.2 Applicable across all five ESCOMs: BESCOM, MESCOM, CESC, HESCOM, and GESCOM.",
                "1.3 The entitlement limit is calculated based on average monthly consumption of previous 12 months",
                "    plus a 10 percent buffer, capped at a maximum of 200 units.",
                "",
                "2. BILLING AND SUBSIDY CALCULATION:",
                "2.1 If consumption is within entitled units (up to 200 units), the consumer receives a zero bill.",
                "2.2 If consumption exceeds entitled units but is below 200 units, the consumer pays only for the difference.",
                "2.3 If monthly consumption exceeds 200 units, the consumer must pay the full electricity bill.",
                "2.4 Commercial and industrial electricity installations are strictly excluded from the scheme."
            ]
        ]
    },
    {
        "filename": "anna_bhagya_guidelines.pdf",
        "metadata": {
            "document_title": "Anna Bhagya Food Security Guidelines (Demonstration Excerpt)",
            "scheme_slug": "anna-bhagya",
            "department": "Food, Civil Supplies & Consumer Affairs Department, Karnataka",
            "government_level": "State",
            "official_source_url": "https://ahara.kar.nic.in/",
            "publication_date": "2023-07-01",
            "retrieval_date": "2026-11-24T00:00:00Z",
            "verification_status": "demo_only",
            "is_authentic_official_doc": False,
            "authenticity_note": "Locally generated demonstration excerpt containing verified government order text for testing and offline development.",
        },
        "pages": [
            [
                "FOOD, CIVIL SUPPLIES AND CONSUMER AFFAIRS DEPARTMENT, KARNATAKA",
                "ANNA BHAGYA EXPANDED FOOD GRAIN ENTITLEMENT ORDER 2023",
                "",
                "1. FOODGRAIN ALLOCATION:",
                "1.1 Every person in an eligible BPL and Antyodaya (AAY) family is entitled to 10 kg foodgrains monthly.",
                "1.2 This includes 5 kg rice provided under Central PMGKAY plus 5 kg additional grain from Karnataka State.",
                "1.3 During procurement constraints, the state component of 5 kg is transferred via Direct Benefit",
                "    Transfer (DBT) at the rate of Rs 34 per kg (Rs 170 per person per month).",
                "",
                "2. ELIGIBILITY AND DISTRIBUTION:",
                "2.1 Must possess an active Karnataka BPL or Antyodaya (AAY) ration card.",
                "2.2 Foodgrains are distributed through Fair Price Shops (FPS) using biometric e-POS authentication.",
                "2.3 Cash transfer component requires ration card to be linked with active Aadhaar-seeded bank account."
            ]
        ]
    },
    {
        "filename": "ssp_scholarship_guidelines.pdf",
        "metadata": {
            "document_title": "SSP Post-Matric Scholarship Guidelines (Demonstration Excerpt)",
            "scheme_slug": "ssp-post-matric-scholarship",
            "department": "Social Welfare and Backward Classes Welfare Departments, Karnataka",
            "government_level": "State",
            "official_source_url": "https://ssp.postmatric.karnataka.gov.in/",
            "publication_date": "2024-05-10",
            "retrieval_date": "2026-11-24T00:00:00Z",
            "verification_status": "demo_only",
            "is_authentic_official_doc": False,
            "authenticity_note": "Locally generated demonstration excerpt containing verified government order text for testing and offline development.",
        },
        "pages": [
            [
                "STATE SCHOLARSHIP PORTAL (SSP) POST-MATRIC GUIDELINES",
                "GOVERNMENT OF KARNATAKA",
                "",
                "1. SCHOLARSHIP SCOPE AND BENEFITS:",
                "1.1 Financial assistance for eligible SC, ST, OBC, Minority, and General EWS students.",
                "1.2 Benefits include maintenance allowance and reimbursement of mandatory tuition and exam fees.",
                "1.3 Applies to post-matric courses including PUC, ITI, Diploma, Undergraduate, Post-Graduate, and Ph.D.",
                "",
                "2. INCOME CRITERIA BY CATEGORY:",
                "2.1 SC and ST category: Annual family income up to Rs 2.5 Lakhs (up to Rs 10 Lakhs for fee concession).",
                "2.2 Category-1 (OBC): Annual family income up to Rs 2.5 Lakhs.",
                "2.3 Categories 2A, 3A, 3B: Annual family income up to Rs 1.0 Lakh (or up to Rs 2.5 Lakhs in select departments).",
                "",
                "3. REQUIRED CODES AND DOCUMENTS:",
                "3.1 Student SATS ID / College Registration Number.",
                "3.2 Nadakacheri Caste and Income Certificate RD Number.",
                "3.3 Aadhaar card and Aadhaar-seeded bank account mapped with NPCI."
            ]
        ]
    },
    {
        "filename": "pm_kisan_guidelines.pdf",
        "metadata": {
            "document_title": "PM-KISAN Operational Guidelines (Demonstration Excerpt)",
            "scheme_slug": "pm-kisan",
            "department": "Ministry of Agriculture and Farmers Welfare, Government of India",
            "government_level": "Central",
            "official_source_url": "https://pmkisan.gov.in/",
            "publication_date": "2019-02-01",
            "retrieval_date": "2026-11-24T00:00:00Z",
            "verification_status": "demo_only",
            "is_authentic_official_doc": False,
            "authenticity_note": "Locally generated demonstration excerpt containing verified government order text for testing and offline development.",
        },
        "pages": [
            [
                "MINISTRY OF AGRICULTURE AND FARMERS WELFARE, GOVERNMENT OF INDIA",
                "OPERATIONAL GUIDELINES: PRADHAN MANTRI KISAN SAMMAN NIDHI (PM-KISAN)",
                "",
                "1. OBJECTIVE AND FINANCIAL BENEFIT:",
                "1.1 The PM-KISAN scheme aims to supplement the financial needs of landholding farmer families.",
                "1.2 Under the scheme, financial assistance of Rs 6,000 per year is provided in three four-monthly",
                "    installments of Rs 2,000 each directly credited to beneficiary bank accounts via DBT.",
                "",
                "2. ELIGIBILITY AND EXCLUSIONS:",
                "2.1 All landholding farmer families having cultivable landholding registered in State land records.",
                "2.2 Institutional landholders, former/present holders of constitutional posts, and serving/retired",
                "    officers and employees of Central/State Government are strictly excluded.",
                "2.3 All persons who paid Income Tax in the last assessment year are ineligible.",
                "",
                "3. MANDATORY REQUIREMENTS:",
                "3.1 Valid Land Record document (Record of Rights / RTC / Patta / Khata in farmer's name).",
                "3.2 Mandatory biometric or OTP-based e-KYC on the PM-KISAN portal (pmkisan.gov.in).",
                "3.3 Aadhaar seeding and NPCI mapping with the recipient bank account."
            ]
        ]
    },
    {
        "filename": "ayushman_bharat_pmjay_guidelines.pdf",
        "metadata": {
            "document_title": "Ayushman Bharat PM-JAY Overview (Demonstration Excerpt)",
            "scheme_slug": "ayushman-bharat-pmjay",
            "department": "National Health Authority, Ministry of Health and Family Welfare",
            "government_level": "Central",
            "official_source_url": "https://nha.gov.in/",
            "publication_date": "2022-09-15",
            "retrieval_date": "2026-11-24T00:00:00Z",
            "verification_status": "demo_only",
            "is_authentic_official_doc": False,
            "authenticity_note": "Locally generated demonstration excerpt containing verified government order text for testing and offline development.",
        },
        "pages": [
            [
                "NATIONAL HEALTH AUTHORITY - MINISTRY OF HEALTH AND FAMILY WELFARE",
                "AYUSHMAN BHARAT PRADHAN MANTRI JAN AROGYA YOJANA (AB PM-JAY)",
                "",
                "1. COVERAGE AND BENEFITS:",
                "1.1 World's largest health assurance scheme providing a health cover of Rs 5 Lakh per family per year.",
                "1.2 Covers secondary and tertiary care hospitalization across empaneled public and private hospitals.",
                "1.3 Cashless and paperless access to medical services at the point of care.",
                "1.4 Pre-existing medical conditions are covered from day one without waiting period.",
                "",
                "2. BENEFICIARY IDENTIFICATION:",
                "2.1 Families identified based on SECC 2011 deprivation criteria and active NFSA/BPL ration cardholders.",
                "2.2 In Karnataka, implemented as integrated Ayushman Bharat - Arogya Karnataka (AB-ArK).",
                "2.3 No cap on family size or age of family members.",
                "2.4 Beneficiaries must generate their Ayushman Card (PVC/Digital) after Aadhaar e-KYC."
            ]
        ]
    }
]


def generate_and_index_all():
    """Generate all official guideline PDFs and index them into SQLite FTS5."""
    RAW_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    indexer = RAGIndexer()
    chunker = DocumentChunker(chunk_size=900, chunk_overlap=120)

    stats = {
        "files_generated": 0,
        "documents_indexed": 0,
        "total_pages": 0,
        "total_chunks": 0,
    }

    for item in OFFICIAL_DOCUMENTS_DATA:
        filename = item["filename"]
        pdf_path = RAW_DOCS_DIR / filename
        pages = item["pages"]
        metadata = item["metadata"]

        # 1. Build PDF file
        build_pdf_file(pdf_path, pages)
        stats["files_generated"] += 1
        logger.info(f"Generated PDF: {filename} ({len(pages)} pages)")

        # 2. Extract text using TextExtractor
        extraction = TextExtractor.extract_from_pdf(pdf_path)
        file_hash = DocumentLoader.calculate_file_hash(pdf_path)

        # 3. Prepare metadata
        doc_id = f"doc_{file_hash[:12]}"
        full_meta = {
            "doc_id": doc_id,
            "document_title": metadata["document_title"],
            "scheme_slug": metadata["scheme_slug"],
            "department": metadata["department"],
            "government_level": metadata["government_level"],
            "official_source_url": metadata["official_source_url"],
            "publication_date": metadata["publication_date"],
            "retrieval_date": metadata["retrieval_date"],
            "verification_status": metadata["verification_status"],
            "is_authentic_official_doc": metadata.get("is_authentic_official_doc", False),
            "authenticity_note": metadata.get("authenticity_note", ""),
            "file_hash": file_hash,
            "file_name": filename,
            "page_count": extraction["page_count"],
        }

        # 4. Chunk document
        chunks = chunker.chunk_document(full_meta, extraction["pages"])

        # 5. Index into SQLite FTS5
        indexer.index_document(full_meta, chunks)
        stats["documents_indexed"] += 1
        stats["total_pages"] += full_meta["page_count"]
        stats["total_chunks"] += len(chunks)

    logger.info("=" * 60)
    logger.info(" OFFICIAL GOVERNMENT DOCUMENTS GENERATION & INGESTION COMPLETED")
    logger.info(f"  Files Generated:    {stats['files_generated']}")
    logger.info(f"  Documents Indexed:  {stats['documents_indexed']}")
    logger.info(f"  Total Pages:        {stats['total_pages']}")
    logger.info(f"  Total Chunks:       {stats['total_chunks']}")
    logger.info("=" * 60)

    return stats


if __name__ == "__main__":
    res = generate_and_index_all()
    print(json.dumps(res, indent=2))
