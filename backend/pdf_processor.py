import fitz  # PyMuPDF
import os
from typing import List, Dict

def extract_chunks_from_pdf(pdf_path: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[Dict]:
    doc = fitz.open(pdf_path)
    chunks = []
    source_name = os.path.basename(pdf_path)

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if not text:
            continue

        words = text.split()
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append({
                "text": chunk_text,
                "page": page_num + 1,
                "source": source_name
            })
            if end >= len(words):
                break
            start += (chunk_size - chunk_overlap)

    doc.close()
    return chunks
