"""Audit sessions: the glue used by the API, the CLI and the evaluation harness."""

from __future__ import annotations

import base64
import time
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import cv2

from .compose import coverage, figure_proof, fmt_figure, line_match, render_finding, summary
from .context import resolve
from .extraction import needs_confirmation, read_bill, validate
from .extraction.parse import _is_itemised
from .figures import FigureStore
from .kb import KnowledgeBase
from .models import AuditResult, Bill, BillHeader, BillLine, Evidence, Origin, Role
from .rules import line_verdicts, run

TTL_SECONDS = 24 * 3600


@dataclass
class Session:
    id: str
    bill: Bill
    figs: FigureStore
    images: list = field(default_factory=list)
    answers: dict = field(default_factory=dict)
    result: AuditResult | None = None
    voice: dict = field(default_factory=dict)   # (lang, ai) -> spoken script, cleared on rerun
    chat: list = field(default_factory=list)    # answers given, so their audio speaks the same words
    schemes: dict = field(default_factory=dict) # state -> kk.schemes.compute() result, cleared on rerun
    tracker_figs: dict = field(default_factory=dict)  # escalation step part -> figure id (kk/tracker.py)
    created: float = field(default_factory=time.time)


class Auditor:
    def __init__(self, kb: KnowledgeBase | None = None) -> None:
        self.kb = kb or KnowledgeBase()
        self.sessions: dict[str, Session] = {}

    # -------------------------------------------------------------- creation
    def audit_files(self, paths: list[str], answers: dict | None = None) -> Session:
        figs = FigureStore()
        sid = uuid.uuid4().hex[:12]
        bill, images = read_bill(paths, figs, sid)
        s = Session(sid, bill, figs, images, dict(answers or {}))
        self.sessions[sid] = s
        return self.rerun(s)

    def audit_structured(self, payload: dict, answers: dict | None = None) -> Session:
        """Bill typed in by a help-desk volunteer (values are user-confirmed, not OCR)."""
        figs = FigureStore()
        sid = uuid.uuid4().hex[:12]
        h = payload.get("header", {})
        header = BillHeader(
            hospital_name=h.get("hospital_name"), gstin=h.get("gstin"),
            admission_date=date.fromisoformat(h["admission_date"]) if h.get("admission_date") else None,
            discharge_date=date.fromisoformat(h["discharge_date"]) if h.get("discharge_date") else None,
            bill_type=h.get("bill_type"), scheme_markers=h.get("scheme_markers", []))
        if h.get("total") not in (None, ""):
            header.total_fig = figs.from_bill(Decimal(str(h["total"])), "INR", Role.TOTAL, [], None, 1.0)
        lines = []
        for i, ln in enumerate(payload.get("lines", []), start=1):
            line = BillLine(id=f"L{i}", description=ln["description"], section=ln.get("section"),
                            batch=ln.get("batch"), expiry=ln.get("expiry"),
                            item_date=date.fromisoformat(ln["date"]) if ln.get("date") else None, confirmed=True)
            for key, attr, role, unit in (("qty", "qty_fig", Role.QUANTITY, "count"),
                                          ("rate", "rate_fig", Role.UNIT_RATE, "INR"),
                                          ("mrp", "mrp_fig", Role.MRP, "INR"),
                                          ("gst_rate", "gst_rate_fig", Role.GST_RATE, "percent"),
                                          ("gst_amount", "gst_amount_fig", Role.GST_AMOUNT, "INR"),
                                          ("amount", "amount_fig", Role.BILLED_AMOUNT, "INR")):
                if ln.get(key) not in (None, ""):
                    fid = figs.add(Decimal(str(ln[key])), unit, role, Origin.USER,
                                   Evidence(note="typed from the paper bill"), money=(unit == "INR"))
                    setattr(line, attr, fid)
            lines.append(line)
        bill = Bill(id=sid, header=header, lines=lines)
        # same lump-sum test as for scanned bills, unless the caller states it explicitly
        bill.itemised = payload["itemised"] if "itemised" in payload else _is_itemised(lines, figs)
        validate(bill, figs)
        s = Session(sid, bill, figs, [], dict(answers or {}))
        self.sessions[sid] = s
        return self.rerun(s)

    # -------------------------------------------------------------- updates
    def rerun(self, s: Session) -> Session:
        ctx = resolve(s.bill, self.kb, s.answers)
        s.result = run(s.bill, ctx, self.kb, s.figs, s.answers)
        s.voice.clear()
        s.schemes.clear()
        s.chat.clear()
        return s

    def voice(self, s: Session, lang: str = "en", ai: bool = True, llm=None) -> dict:
        """Spoken summary, cached so the captions and any server audio are the same script."""
        from .voice import build
        key = (lang, ai)
        if key not in s.voice:
            s.voice[key] = build(s.result, lang, ai=ai, llm=llm)
        return s.voice[key]

    def set_answers(self, sid: str, answers: dict) -> Session:
        s = self.get(sid)
        s.answers.update({k: v for k, v in answers.items() if v is not None})
        return self.rerun(s)

    def confirm(self, sid: str, corrections: dict[str, dict], confirmed: list[str]) -> Session:
        """corrections: {line_id: {"qty": "2", "rate": "100", "amount": "200"}}; confirmed: line ids accepted as read."""
        s = self.get(sid)
        attr = {"qty": ("qty_fig", Role.QUANTITY, "count"), "rate": ("rate_fig", Role.UNIT_RATE, "INR"),
                "amount": ("amount_fig", Role.BILLED_AMOUNT, "INR"), "mrp": ("mrp_fig", Role.MRP, "INR")}
        lines = {l.id: l for l in s.bill.lines}
        for lid, vals in corrections.items():
            line = lines[lid]
            for k, v in vals.items():
                a, role, unit = attr[k]
                old = getattr(line, a)
                if old:
                    setattr(line, a, s.figs.confirm(old, Decimal(str(v))))
                else:
                    setattr(line, a, s.figs.add(Decimal(str(v)), unit, role, Origin.USER,
                                                Evidence(note="entered by user"), money=(unit == "INR")))
            confirmed = list(confirmed) + [lid]
        for lid in confirmed:
            line = lines[lid]
            line.confirmed = True
            line.flags = [f for f in line.flags if f not in ("low_ocr_confidence", "ambiguous_columns",
                                                             "photo_arith_unverified", "arith_mismatch")]
        validate(s.bill, s.figs)
        return self.rerun(s)

    def get(self, sid: str) -> Session:
        self.expire()
        if sid not in self.sessions:
            raise KeyError(sid)
        return self.sessions[sid]

    def delete(self, sid: str) -> None:
        self.sessions.pop(sid, None)

    def expire(self) -> None:
        now = time.time()
        for sid in [k for k, s in self.sessions.items() if now - s.created > TTL_SECONDS]:
            del self.sessions[sid]

    # -------------------------------------------------------------- scheme savings
    def schemes(self, s: Session, state: str | None, lang: str = "en") -> dict:
        """What a government scheme could have paid on this bill (awareness only, kk/schemes.py)."""
        from . import schemes as sch
        from .compose.render import schemes_panel
        if not sch.applies(s.answers):
            return {"applies": False}, {}
        key = sch.norm_state(state) or ""
        if key not in s.schemes:
            before = set(s.figs.all())
            s.schemes[key] = sch.compute(s.bill, s.figs, key or None)
            s.result.figures.update({k: v for k, v in s.figs.all().items() if k not in before})
        res = s.schemes[key]
        panel = schemes_panel(res, s.result.figures, lang)
        for group in ("state_rows", "central"):
            for r in panel[group]:
                r["source_title"] = self.kb.source_title(r["source"])
                r["source_url"] = self.kb.source_url(r["source"])
        return panel, {fid: figure_proof(fid, s.result, self.kb) for fid in self._proof_closure(s, sch.fig_ids(res))}

    def tracker(self, s: Session, channel: str, events: dict | None = None, cause_on: str | None = None,
                lang: str = "en", today=None) -> tuple[dict, dict]:
        """Complaint timeline for one channel (kk/tracker.py): reply due dates, last days to file,
        the next step, and calendar entries. The family records dates; nothing is filed for them."""
        from datetime import date as _date
        from . import tracker as trk
        from .compose.render import tracker_panel
        cfg = trk.load(self.kb.dir)
        cause = trk._day(cause_on) or s.bill.header.discharge_date or s.bill.header.admission_date
        before = set(s.figs.all())
        res = trk.plan(cfg, channel, events or {}, s.figs, s.tracker_figs, cause_on=cause,
                       today=trk._day(today) if today else _date.today())
        s.result.figures.update({k: v for k, v in s.figs.all().items() if k not in before})
        panel = tracker_panel(res, s.result.figures, lang, self.kb)
        panel["ics"] = trk.ics(panel["calendar"], f"Kharcha Kavach: {panel['title']}")
        for e in panel["calendar"]:
            e["date"] = e["date"].isoformat()
        return panel, {fid: figure_proof(fid, s.result, self.kb) for fid in self._proof_closure(s, trk.fig_ids(res))}

    def insurance(self, s: Session, deductions: list[dict], cashless: bool | None = None,
                  lang: str = "en") -> tuple[dict, dict]:
        """Check what an insurer cut from a claim against IRDAI's standard lists (kk/insurance.py)."""
        from . import insurance as ins
        from . import tracker as trk
        from .compose.render import insurance_panel
        before = set(s.figs.all())
        w = trk.load(self.kb.dir)["steps"]["insurer_gro"]["wait"]
        wait = trk._fig(s.figs, s.tracker_figs, "insurer_gro", "wait", w["days"], "days", Role.WAIT_DAYS,
                        w["source"], w["ref"])
        res = ins.check(s.bill, s.figs, self.kb, deductions, cashless, wait)
        s.result.figures.update({k: v for k, v in s.figs.all().items() if k not in before})
        panel = insurance_panel(res, s.result.figures, lang, self.kb)
        return panel, {fid: figure_proof(fid, s.result, self.kb) for fid in self._proof_closure(s, ins.fig_ids(res))}

    def _proof_closure(self, s: Session, ids) -> list[str]:
        seen, queue = [], list(ids)
        while queue:
            fid = queue.pop()
            if fid in seen or fid not in s.result.figures:
                continue
            seen.append(fid)
            queue.extend(s.result.figures[fid].evidence.inputs or [])
        return seen

    # -------------------------------------------------------------- views
    def view(self, s: Session, lang: str = "en") -> dict:
        r = s.result
        verdicts = line_verdicts(r)
        used_figs = set()
        findings = []
        for f in r.findings:
            rf = render_finding(f, r, lang)
            rf["basis"] = self.kb.basis(f.source_ids)
            findings.append(rf)
            used_figs.update(seg["fig"] for seg in rf["text"] if "fig" in seg)
        cov = coverage(r, lang)
        matches = {l.id: line_match(r, l.id, lang) for l in s.bill.lines}
        for extra in (r.recoverable_fig, r.amber_total_fig, r.hospital_fig, r.scheme_fig, r.fallback_fig,
                      *r.coverage.values()):
            if extra:
                used_figs.add(extra)
        proofs = {}
        queue = list(used_figs)
        while queue:   # include formula inputs so every proof chain is complete
            fid = queue.pop()
            if fid in proofs:
                continue
            proofs[fid] = figure_proof(fid, r, self.kb)
            for inp in proofs[fid].get("formula", {}).get("inputs", []):
                queue.append(inp["id"])
        schemes_panel, scheme_proofs = self.schemes(s, s.answers.get("state"), lang)
        proofs.update(scheme_proofs)
        from .compose.render import CATALOG, msg as _msg, segments as _seg
        more_ui = {k: _msg(k, lang) for k in CATALOG["en"] if k.startswith(("trk_l_", "ins_l_"))}
        more_ui.update({"ins_title": _msg("ins_title", lang), "trk_title": _msg("trk_title", lang)})
        return {
            "id": s.id,
            "language": lang,
            "schemes": schemes_panel,
            "more_ui": more_ui,
            "ins_intro": _seg(_msg("ins_intro", lang), {}, {}, r.figures),
            "payer": s.answers.get("payer"),
            "summary": summary(r, lang),
            "coverage": cov,
            "remedy": {"hospital": r.hospital_fig, "scheme": r.scheme_fig, "fallback": r.fallback_fig},
            "warnings": s.bill.warnings,
            "header": s.bill.header.model_dump(mode="json"),
            "total_display": fmt_figure(s.figs.get(s.bill.header.total_fig)) if s.bill.header.total_fig else None,
            "total_fig": s.bill.header.total_fig,
            "pages": s.bill.pages if s.images else 0,   # typed-in bills have no page images
            "lines": [{"id": l.id, "description": l.description, "section": l.section,
                       "bbox": l.bbox.model_dump() if l.bbox else None, "flags": l.flags,
                       "verdict": verdicts[l.id].value,
                       "match": matches[l.id],
                       "qty": l.qty_fig, "rate": l.rate_fig, "amount": l.amount_fig, "mrp": l.mrp_fig,
                       "values": {k: str(s.figs.value(fid)) for k, fid in
                                  (("qty", l.qty_fig), ("rate", l.rate_fig), ("amount", l.amount_fig)) if fid},
                       "display": {k: fmt_figure(s.figs.get(fid)) for k, fid in
                                   (("qty", l.qty_fig), ("rate", l.rate_fig), ("amount", l.amount_fig)) if fid}}
                      for l in s.bill.lines],
            "needs_confirmation": needs_confirmation(s.bill),
            "findings": findings,
            "proofs": proofs,
            "recoverable_fig": r.recoverable_fig,
            "amber_total_fig": r.amber_total_fig,
            "context": r.context.model_dump(mode="json"),
            "data_versions": r.data_versions,
        }

    def page_png(self, s: Session, page: int) -> bytes:
        img = s.images[page - 1]
        ok, buf = cv2.imencode(".png", img)
        return buf.tobytes()

    def crop_png(self, s: Session, fid: str, pad: int = 12) -> bytes | None:
        f = s.result.figures.get(fid)
        if not f or not f.evidence.bbox or not s.images:
            return None
        b = f.evidence.bbox
        img = s.images[b.page - 1]
        h, w = img.shape[:2]
        x0, y0 = max(0, int(b.x0) - pad), max(0, int(b.y0) - pad)
        x1, y1 = min(w, int(b.x1) + pad), min(h, int(b.y1) + pad)
        crop = img[y0:y1, x0:x1]
        if crop.size == 0:
            return None
        ok, buf = cv2.imencode(".png", crop)
        return buf.tobytes()

    def line_crop_png(self, s: Session, lid: str, pad: int = 14) -> bytes | None:
        """The whole bill line as photographed, so the family sees what could not be read."""
        line = next((l for l in s.bill.lines if l.id == lid), None)
        if not line or not line.bbox or not s.images:
            return None
        b = line.bbox
        img = s.images[b.page - 1]
        h, w = img.shape[:2]
        x0, x1 = max(0, int(b.x0) - pad), min(w, int(b.x1) + pad)
        y0, y1 = max(0, int(b.y0) - pad), min(h, int(b.y1) + pad)
        nums = [s.result.figures[f].evidence.bbox for f in (line.qty_fig, line.rate_fig, line.amount_fig)
                if f and f in s.result.figures and s.result.figures[f].evidence.bbox]
        if nums and (x1 - x0) > 6 * (y1 - y0):
            # a long thin line is unreadable on a phone: keep the number columns, where the doubt is
            x0 = max(x0, int(min(n.x0 for n in nums)) - 120)
        crop = img[y0:y1, x0:x1]
        if crop.size == 0:
            return None
        ok, buf = cv2.imencode(".png", crop)
        return buf.tobytes()

    def crop_b64(self, s: Session, fid: str) -> str | None:
        png = self.crop_png(s, fid)
        return base64.b64encode(png).decode() if png else None
