"""Bill reading: files in, structured Bill (plus its figures) out."""

from __future__ import annotations

import uuid
from pathlib import Path

from ..figures import FigureStore
from ..models import Bill, Word
from .ocr import ocr_image, pdf_words
from .parse import build_bill
from .preprocess import prepare
from .validate import validate


def read_bill(paths: list[str], figs: FigureStore, bill_id: str | None = None) -> tuple[Bill, list]:
    """Read one bill made of one or more files (PDF pages or photos, in order).

    Returns the Bill and the page images (for the proof panel crops).
    """
    words: list[Word] = []
    images = []
    warnings: list[str] = []
    page_no = 0
    for p in paths:
        suffix = Path(p).suffix.lower()
        if suffix == ".pdf":
            w, n, imgs = pdf_words(p)
            for word in w:   # renumber pages across files
                word.bbox.page += page_no
            words.extend(_reid(w, len(words)))
            images.extend(imgs)
            page_no += n
        else:
            page_no += 1
            img, quality, _angle = prepare(p)
            warnings.extend(quality.warnings)
            images.append(img)
            words.extend(ocr_image(img, page_no, len(words)))
    bill = build_bill(words, page_no, figs, bill_id or uuid.uuid4().hex[:12], source_files=[Path(p).name for p in paths])
    bill.warnings.extend(sorted(set(warnings)))
    validate(bill, figs)
    return bill, images


def _reid(words: list[Word], offset: int) -> list[Word]:
    return [w.model_copy(update={"id": f"p{w.bbox.page}w{offset + i}"}) for i, w in enumerate(words)]
