"""Command-line interface.

  python -m kk audit bill.pdf [page2.jpg ...] --payer cash --state karnataka --lang kn --out report.html
  python -m kk serve [--port 8000]
  python -m kk kb check
  python -m kk kb import-nppa notification.pdf --source-id nppa_scheduled_ceilings --valid-from 2026-04-01 --valid-to 2027-03-31
  python -m kk kb import-hbp hbp2022_state_copy.pdf --source-id hbp_2022 --valid-from 2022-01-01
  python -m kk kb import-empanelment hospitals.csv --source-id pmjay_empanelment --status-from 2026-11-01
  python -m kk kb approve data/staged/nppa.csv --table nppa_scheduled_ceilings --reviewer "Name"
  python -m kk eval eval/cases
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="kk", description="Kharcha Kavach hospital bill auditor")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit", help="audit a bill (PDF and/or photos in page order, or one typed .json bill)")
    a.add_argument("files", nargs="+")
    a.add_argument("--payer", choices=["pmjay", "state_scheme", "cghs", "private_insurance", "cash"])
    a.add_argument("--state")
    a.add_argument("--lang", default="en", choices=["en", "hi", "kn", "gu", "ta", "te"])
    a.add_argument("--service-date")
    a.add_argument("--hospital-empanelled", choices=["yes", "no"])
    a.add_argument("--scheme-booked", choices=["yes", "no"])
    a.add_argument("--patient-paid", choices=["yes", "no"])
    a.add_argument("--medicine-units-confirmed", action="store_true")
    a.add_argument("--out", help="write the HTML report here")
    a.add_argument("--json", action="store_true", help="print the full result as JSON")

    s = sub.add_parser("serve", help="run the web app and API")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)

    kb = sub.add_parser("kb", help="knowledge base tools")
    kbs = kb.add_subparsers(dest="kbcmd", required=True)
    kbs.add_parser("check", help="load and validate every table")
    for name in ("import-nppa", "import-hbp"):
        p = kbs.add_parser(name)
        p.add_argument("pdf")
        p.add_argument("--source-id", required=True)
        p.add_argument("--valid-from", required=True)
        p.add_argument("--valid-to", default="")
        p.add_argument("--out")
    p = kbs.add_parser("import-empanelment")
    p.add_argument("csv")
    p.add_argument("--source-id", required=True)
    p.add_argument("--status-from", required=True)
    p.add_argument("--status", default="empanelled", choices=["empanelled", "suspended", "de-empanelled"])
    p.add_argument("--out")
    p = kbs.add_parser("approve")
    p.add_argument("staged")
    p.add_argument("--table", required=True)
    p.add_argument("--reviewer", required=True)
    p.add_argument("--yes", action="store_true", help="confirm every row was checked against the source PDF")

    e = sub.add_parser("eval", help="evaluate on real labelled cases")
    e.add_argument("cases_dir")

    args = ap.parse_args(argv)

    if args.cmd == "audit":
        from .compose import plain, render_finding, summary
        from .report import render_report
        from .service import Auditor

        yn = lambda v: None if v is None else v == "yes"
        answers = {"payer": args.payer, "state": args.state, "service_date": args.service_date,
                   "hospital_empanelled": yn(args.hospital_empanelled), "scheme_booked": yn(args.scheme_booked),
                   "patient_paid": yn(args.patient_paid),
                   "medicine_qty_in_dosage_units": True if args.medicine_units_confirmed else None}
        answers = {k: v for k, v in answers.items() if v is not None}
        aud = Auditor()
        if len(args.files) == 1 and args.files[0].lower().endswith(".json"):
            # a typed bill: {"bill": {...}, "answers": {...}} as in tests/fixtures, or a bare bill
            doc = json.loads(Path(args.files[0]).read_text(encoding="utf-8"))
            payload = doc.get("bill", doc)
            sess = aud.audit_structured(payload, {**doc.get("answers", {}), **answers})
        else:
            sess = aud.audit_files(args.files, answers)
        if args.json:
            print(json.dumps(aud.view(sess, args.lang), ensure_ascii=False, indent=2, default=str))
        else:
            for line in summary(sess.result, args.lang):
                print(plain(line))
            print()
            for f in sess.result.findings:
                r = render_finding(f, sess.result, args.lang)
                if r["verdict"] == "green":
                    continue
                print(f"[{r['verdict_label']}] {r['title']} ({r['rule_id']}, {r['legal_label']})")
                print("   " + plain(r["text"]))
                for c in r["conditions"]:
                    print("   • " + c)
                for x in r["asks"]:
                    print("   → " + x)
        if args.out:
            Path(args.out).write_text(render_report(aud, sess, args.lang), encoding="utf-8")
            print(f"\nReport written to {args.out}")
        return 0

    if args.cmd == "serve":
        import uvicorn
        uvicorn.run("kk.api:app", host=args.host, port=args.port)
        return 0

    if args.cmd == "kb":
        from .kb import KnowledgeBase
        from .kb import importers as im

        k = KnowledgeBase()
        if args.kbcmd == "check":
            rd = k.readiness()
            print(json.dumps({"rows": {t: len(v) for t, v in k.tables.items()}, "rules": len(k.rules),
                              "versions": k.versions}, indent=2))
            print(f"\nRules ready: {rd['ready']} of {rd['total']}")
            for x in rd["rules"]:
                why = "" if x["ready"] else (" - on hold" if x["legal_status"] == "on_hold" else
                                             " - load: " + ", ".join(x["missing"]))
                print(f"  {'ready  ' if x['ready'] else 'NOT    '} {x['rule']}{why}")
            for f in rd["staged_awaiting_review"]:
                print(f"  staged, awaiting review: data/staged/{f}")
            return 0
        staged = k.dir / "staged"
        if args.kbcmd == "import-nppa":
            out = Path(args.out or staged / (Path(args.pdf).stem + "_nppa.csv"))
            n = im.import_nppa_ceilings(Path(args.pdf), args.source_id, args.valid_from, args.valid_to, out)
        elif args.kbcmd == "import-hbp":
            out = Path(args.out or staged / (Path(args.pdf).stem + "_hbp.csv"))
            n = im.import_hbp(Path(args.pdf), args.source_id, args.valid_from, args.valid_to, out)
        elif args.kbcmd == "import-empanelment":
            out = Path(args.out or staged / (Path(args.csv).stem + "_empanelment.csv"))
            n = im.import_empanelment_csv(Path(args.csv), args.source_id, args.status_from, out, args.status)
        elif args.kbcmd == "approve":
            if not args.yes:
                print("Refusing: re-run with --yes only after checking every staged row against the source PDF.")
                return 2
            n = im.approve(Path(args.staged), args.table, args.reviewer, k)
            print(f"Approved {n} rows into {args.table} (logged in data/review_log.csv)")
            return 0
        print(f"Staged {n} rows in {out}. Review them against the PDF, then run `kk kb approve`.")
        return 0

    if args.cmd == "eval":
        from .evaluation import evaluate
        print(json.dumps(evaluate(args.cases_dir), indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
