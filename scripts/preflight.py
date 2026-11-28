"""Pre-flight check for the stage demo. Run it on the demo laptop an hour before presenting.

    python scripts/preflight.py            # checks everything, writes offline backups to demo_assets/
    python scripts/preflight.py --lang kn  # voice and letter in Kannada instead of Hindi

Each step prints PASS / WARN / FAIL with the time it took. Exit code 1 if anything failed.
Backups (spoken summary MP3, printable report, letters) let the demo go on if a live step breaks.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BILLS = ROOT / "tests" / "fixtures" / "sample_bills"
OUT = ROOT / "demo_assets"
results: list[tuple[str, str, str]] = []


def step(name):
    def wrap(fn):
        def run(*a, **k):
            t = time.time()
            try:
                status, note = fn(*a, **k)
            except Exception as e:  # a demo check must report, not crash
                status, note = "FAIL", f"{type(e).__name__}: {e}"
            results.append((status, name, f"{note} ({time.time() - t:.1f}s)"))
            print(f"{status:5} {name}: {note} ({time.time() - t:.1f}s)", flush=True)
        return run
    return wrap


def case(name):
    return json.loads((BILLS / f"{name}.json").read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="hi", choices=["en", "hi", "kn", "gu", "ta", "te"])
    lang = ap.parse_args().lang
    OUT.mkdir(exist_ok=True)

    from kk.compose.verifier import verify
    from kk.grievance import letters
    from kk.report import render_report
    from kk.service import Auditor
    from kk.voice import quality, synthesize

    aud = Auditor()
    state = {}

    @step("Knowledge base")
    def kb():
        rd = aud.kb.readiness()
        not_ready = [r["rule"] for r in rd["rules"] if not r["ready"]]
        return "PASS", f"{rd['ready']} of {rd['total']} rules ready; not ready: {', '.join(not_ready) or 'none'}"

    @step("Bill 1 from the PDF (stent, cash)")
    def bill1():
        c = case("bill1_cardiac_cash")
        s = aud.audit_files([str(BILLS / "bill1_cardiac_cash.pdf")], c["answers"])
        state["s1"] = s
        rec = s.figs.value(s.result.recoverable_fig)
        reds = sum(f.verdict.value == "red" for f in s.result.findings)
        if rec != Decimal("20469.34") or reds != 4:
            return "FAIL", f"expected Rs 20,469.34 and 4 red findings, got {rec} and {reds}"
        return "PASS", "Rs 20,469.34 to challenge, 4 red findings"

    @step("Receipt for the stent excess")
    def receipt():
        s = state["s1"]
        v = aud.view(s, lang)
        stent = next(f for f in v["findings"] if f["rule_id"] == "PRC-STENT" and f["verdict"] == "red")
        chain, queue = [], [stent["excess_fig"]]
        while queue:
            p = v["proofs"][queue.pop(0)]
            chain.append(f"{p['display']} ({p['origin']})")
            queue += [i["id"] for i in p.get("formula", {}).get("inputs", [])]
        origins = " ".join(chain)
        if "(bill)" not in origins or "(rule_data)" not in origins:
            return "FAIL", "proof chain does not reach both the bill and the official table: " + origins
        return "PASS", " <- ".join(chain[:5])

    @step(f"Letters ({lang})")
    def lets():
        ls = letters(state["s1"].result, lang, aud.kb.dir)
        for l in ls:
            (OUT / f"letter_{l['channel']}_{lang}.txt").write_text(l["letters"][lang], encoding="utf-8")
        chans = [l["channel"] for l in ls]
        if "hospital_desk" not in chans or "nppa" not in chans:
            return "FAIL", f"expected hospital desk and NPPA letters, got {chans}"
        return "PASS", f"{len(ls)} letters saved to demo_assets/"

    @step(f"Spoken summary ({lang})")
    def voice():
        sc = aud.voice(state["s1"], lang, ai=False)
        audio, media = synthesize(sc["speech_lines"], lang)
        ext = "mp3" if "mpeg" in media else "wav"
        (OUT / f"summary_bill1_{lang}.{ext}").write_bytes(audio)
        q = quality(lang)
        status = "PASS" if q == "natural" else "WARN"
        hint = "" if q == "natural" else " - robotic voice: pip install edge-tts (needs internet), or run scripts/fetch_voices.py (en, hi, gu)"
        return status, f"{len(audio) // 1024} KB {ext}, {q} voice{hint}"

    @step(f"Phone call script ({lang})")
    def call():
        from kk.voice.callscript import build_calls
        calls = build_calls(state["s1"].result, lang)
        hosp = next((c for c in calls if c["who"] == "hospital"), None)
        if not hosp:
            return "FAIL", "no call script for the hospital desk"
        audio, media = synthesize(hosp["speech_lines"], lang)
        (OUT / f"call_hospital_bill1_{lang}.{'mp3' if 'mpeg' in media else 'wav'}").write_bytes(audio)
        return "PASS", f"{len(hosp['speech_lines'])} sentences, audio saved"

    @step(f"Proof card ({lang})")
    def card():
        from kk import proofcard
        png = proofcard.render(aud, state["s1"], lang)
        (OUT / f"proof_card_bill1_{lang}.png").write_bytes(png)
        return "PASS", f"demo_assets/proof_card_bill1_{lang}.png ({len(png) // 1024} KB)"

    @step("Number guard")
    def guard():
        figs = state["s1"].result.figures
        bad = verify("The hospital overcharged you ₹25,000 for the stent.", figs, "en")
        fid = next(f.excess_fig for f in state["s1"].result.findings if f.excess_fig)
        good = verify(f"The hospital charged [{figs[fid].role.value}:{fid}] more than allowed.", figs, "en")
        if bad.ok or not good.ok:
            return "FAIL", f"bad passed={bad.ok}, good passed={good.ok}"
        return "PASS", "a typed amount is blocked; a slot passes and fills from its proof"

    @step("Bill 2 PM-JAY entitlement with official wording")
    def bill2():
        c = case("bill2_knee_pmjay")
        s = aud.audit_structured(c["bill"], c["answers"])
        v = aud.view(s, lang)
        ent = [f for f in v["findings"] if f["rule_id"].startswith("ENT-") and f["verdict"] == "red"]
        if not ent or not all("entire cost of treatment" in " ".join(b["quote"] for b in f["basis"]) for f in ent):
            return "FAIL", "no PM-JAY finding quoting the NHA Operation Manual"
        return "PASS", f"{len(ent)} PM-JAY findings, each quoting NHA Operation Manual, Annexure-1"

    @step("Stained photo asks the user to confirm (opening of the demo)")
    def stained():
        s = aud.audit_files([str(ROOT / "tests/fixtures/demo/bill3_stained_photo.jpg")],
                            {"payer": "cash", "state": "karnataka"})
        need = aud.view(s, lang)["needs_confirmation"]
        if "L2" not in need:
            return "FAIL", f"expected to ask about the stent line L2, asked about {need}"
        if any(f.verdict.value == "red" and f.line_id == "L2" for f in s.result.findings):
            return "FAIL", "a red finding was shown before the user confirmed the stained number"
        s = aud.confirm(s.id, {"L2": {"rate": "52000.00"}}, [l for l in need if l != "L2"])
        if aud.view(s, lang)["needs_confirmation"]:
            return "FAIL", "still asking after confirmation"
        return "PASS", "asks about the stent line (L2), clears after the user types Rs 52,000"

    @step("Printable report (offline backup)")
    def report():
        html = render_report(aud, state["s1"], lang)
        (OUT / f"report_bill1_{lang}.html").write_text(html, encoding="utf-8")
        return "PASS", f"demo_assets/report_bill1_{lang}.html ({len(html) // 1024} KB)"

    @step("Local AI wording (optional)")
    def llm():
        import os
        import urllib.request
        try:
            urllib.request.urlopen(os.environ.get("KK_OLLAMA_URL", "http://localhost:11434") + "/api/tags", timeout=2)
            return "PASS", "Ollama is running"
        except Exception:
            return "WARN", "Ollama not running - templates are used; the demo does not need it"

    for fn in (kb, stained, bill1, receipt, lets, voice, call, card, guard, bill2, report, llm):
        fn()
    fails = [r for r in results if r[0] == "FAIL"]
    print(f"\n{len(results) - len(fails)} of {len(results)} checks passed or warned; {len(fails)} failed.")
    print("Backups in demo_assets/. Open the app with ?demo=1 for the short stage flow.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
