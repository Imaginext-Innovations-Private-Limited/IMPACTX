import { describe, expect, it, vi } from "vitest";
import { en } from "../../src/i18n/en";
import { hi } from "../../src/i18n/hi";
import { kn } from "../../src/i18n/kn";
import { ta } from "../../src/i18n/ta";
import { getLang, notifyNativeLang, parseLang, queryLang, setLang, SUPPORTED_LANGS, t, tx } from "../../src/i18n";
import { checklistItems, checklistTypes } from "../../src/ui/checklist_logic";
import { dehydrationFlags, flagLabel, maternalRedOptions, maternalYellowOptions, pediatricDangerOptions } from "../../src/ui/triage_map";

const DENY = [
  // Perso-Arabic / colloquial words to avoid
  "अस्पताल", "दवा", "दवाई", "दवाख़ाना", "दवाखाना", "बुख़ार", "बुखार", "तकलीफ़", "तकलीफ", "ख़तरा", "खतरा",
  "मरीज़", "मरीज", "इलाज", "सलाह", "ज़रूरी", "जरूरी", "मदद", "ख़ून", "खून", "कमज़ोरी", "कमजोरी",
  "डॉक्टर", "डाक्टर", "एम्बुलेंस", "एंबुलेंस", "फ़ोन", "फोन", "तारीख", "तारीख़", "वापस", "शुरू", "शुरुआत",
  "बंद", "रद्द", "ज़्यादा", "ज्यादा", "साल", "सिर्फ", "ख़त्म", "खत्म", "इस्तेमाल", "कोशिश", "ज़िला", "जिला",
  "ख़बर", "खबर", "वक़्त", "वक्त", "हफ़्ता", "हफ्ता", "बीमारी", "सेहत", "सुबह", "शाम", "जल्दी", "ज़रा",
  // Hinglish / transliterated English
  "मोबाइल", "ऑफलाइन", "ऑफ़लाइन", "ऑनलाइन", "बटन", "सिंक", "रिकॉर्ड", "रिकार्ड", "कार्ड", "नेटवर्क", "हब",
  "सर्वर", "ऐप", "एप्प", "ट्राइएज", "ट्रायज", "मेनू", "सेव", "चेकलिस्ट", "वैक्सीन", "टीका-कार्ड", "ऑक्सीजन",
  "हीमोग्लोबिन", "टेम्परेचर", "वॉइस", "नोट", "रजिस्टर", "रजिस्ट्रेशन", "ट्रिपल",
];
// Nukta letters (decompose to base + U+093C): ख़ ग़ ज़ फ़ ड़ ढ़ क़
const NUKTA = ["ख़", "ग़", "ज़", "फ़", "ड़", "ढ़", "क़"];

describe("i18n tables", () => {
  it("have identical key sets across en, hi, kn, and ta", () => {
    expect(Object.keys(hi).sort()).toEqual(Object.keys(en).sort());
    expect(Object.keys(kn).sort()).toEqual(Object.keys(en).sort());
    expect(Object.keys(ta).sort()).toEqual(Object.keys(en).sort());
  });

  it("have no empty strings and matching {placeholders} across en, hi, kn, and ta", () => {
    const ph = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort().join(",");
    for (const k of Object.keys(en) as (keyof typeof en)[]) {
      expect(en[k].length, k).toBeGreaterThan(0);
      expect(hi[k].length, k).toBeGreaterThan(0);
      expect(kn[k].length, k).toBeGreaterThan(0);
      expect(ta[k].length, k).toBeGreaterThan(0);
      expect(ph(hi[k]), `hi ${k}`).toBe(ph(en[k]));
      expect(ph(kn[k]), `kn ${k}`).toBe(ph(en[k]));
      expect(ph(ta[k]), `ta ${k}`).toBe(ph(en[k]));
    }
  });

  it("Hindi contains no deny-listed Perso-Arabic or Hinglish words", () => {
    for (const [k, v] of Object.entries(hi)) {
      // Whole-word match (so e.g. "साल" does not flag "चिकित्सालय").
      const words = v.split(/[^\u0900-\u097F]+/).filter(Boolean);
      for (const bad of DENY) {
        expect(words, `${k} contains ${bad}`).not.toContain(bad);
        if (bad.includes(" ")) expect(v).not.toContain(bad);
      }
    }
  });

  it("Hindi contains no nukta letters (Perso-Arabic spellings), in any Unicode form", () => {
    for (const [k, v] of Object.entries(hi)) {
      for (const n of NUKTA) {
        expect(v, `${k} has ${n}`).not.toContain(n);
        expect(v.normalize("NFC"), `${k} has ${n}`).not.toContain(n.normalize("NFC"));
      }
      expect(v.normalize("NFD"), `${k} has a nukta`).not.toContain("़");
    }
  });

  it("Hindi strings are Devanagari (Latin allowed only for units, URLs and the language toggle)", () => {
    const allowed = new Set(["lang.switch", "sync.hubHint"]);
    for (const [k, v] of Object.entries(hi)) {
      if (allowed.has(k as never)) continue;
      const stripped = v.replace(/\(°C\)|\(%\)|\(g\/dL\)|\(cm\)|\{\w+\}|108/g, "");
      expect(stripped, k).not.toMatch(/[A-Za-z]/);
    }
  });

  it("the Hindi referral wording uses the mandated vocabulary", () => {
    expect(hi["ref.red"]).toContain("चिकित्सालय भेजें");
    expect(hi["sev.call108"]).toContain("रोगी वाहन");
  });

  it("every canonical rule-table-driven key exists (dehydration labels, checklist titles)", () => {
    for (const f of dehydrationFlags()) expect(`dehy.${f}` in en, f).toBe(true);
    for (const c of ["anc_trimester_1", "anc_trimester_2", "anc_trimester_3", "pnc_mother", "pnc_newborn"]) {
      expect(`ck.${c}` in en, c).toBe(true);
    }
    expect(pediatricDangerOptions().length).toBeGreaterThan(5);
    expect(maternalRedOptions().length).toBeGreaterThan(5);
  });

  it("covers every rule-table flag and checklist item in all four languages (en = canonical label)", () => {
    const enT = en as Record<string, string>;
    const hiT = hi as Record<string, string>;
    const knT = kn as Record<string, string>;
    const taT = ta as Record<string, string>;
    const flags = [...pediatricDangerOptions(), ...maternalRedOptions(), ...maternalYellowOptions()];
    expect(flags.length).toBeGreaterThan(20);
    for (const o of flags) {
      expect(enT[`flag.${o.flag}`], `en flag.${o.flag}`).toBe(o.label);
      expect(hiT[`flag.${o.flag}`], `hi flag.${o.flag}`).toBeTruthy();
      expect(knT[`flag.${o.flag}`], `kn flag.${o.flag}`).toBeTruthy();
      expect(taT[`flag.${o.flag}`], `ta flag.${o.flag}`).toBeTruthy();
    }
    const types = checklistTypes();
    expect(types).toHaveLength(5);
    for (const type of types) {
      expect(checklistItems(type).length, type).toBeGreaterThan(0);
      for (const i of checklistItems(type)) {
        expect(enT[`cki.${i.id}`], `en cki.${i.id}`).toBe(i.label);
        expect(hiT[`cki.${i.id}`], `hi cki.${i.id}`).toBeTruthy();
        expect(knT[`cki.${i.id}`], `kn cki.${i.id}`).toBeTruthy();
        expect(taT[`cki.${i.id}`], `ta cki.${i.id}`).toBeTruthy();
      }
    }
  });

  it("Kannada strings contain Kannada script (U+0C80–U+0CFF) and contextual ASHA terms", () => {
    for (const [k, v] of Object.entries(kn)) {
      expect(v, k).toMatch(/[\u0C80-\u0CFF]/);
    }
    expect(kn["app.name"]).toBe("ಆರೋಗ್ಯ ಸಂಜಾಲ");
    expect(kn["app.subtitle"]).toContain("ಆಶಾ ಕಾರ್ಯಕರ್ತೆ");
    expect(kn["sev.red"]).toContain("ತುರ್ತು ಅಪಾಯ");
    expect(kn["nav.register"]).toBe("ರೋಗಿ ನೋಂದಣಿ");
    expect(kn["vac.title"]).toBe("ಲಸಿಕೆ ವೇಳಾಪಟ್ಟಿ");
    expect(kn["voice.title"]).toBe("ಧ್ವನಿ ಟಿಪ್ಪಣಿ");
  });

  it("Tamil strings contain Tamil script (U+0B80–U+0BFF) and contextual ASHA terms", () => {
    for (const [k, v] of Object.entries(ta)) {
      expect(v, k).toMatch(/[\u0B80-\u0BFF]/);
    }
    expect(ta["app.name"]).toBe("ஆரோக்கிய வலையமைப்பு");
    expect(ta["app.subtitle"]).toContain("ஆஷா பணியாளர்");
    expect(ta["sev.red"]).toContain("அவசர ஆபத்து");
    expect(ta["nav.register"]).toBe("நோயாளி பதிவு");
    expect(ta["vac.title"]).toBe("தடுப்பூசி அட்டவணை");
    expect(ta["voice.title"]).toBe("குரல் குறிப்பு");
  });
});

describe("language switching and helpers", () => {
  it("supports en, hi, kn, and ta switching via setLang/getLang/t/tx", () => {
    expect(SUPPORTED_LANGS).toEqual(["en", "hi", "kn", "ta"]);
    const prev = getLang();
    try {
      setLang("en", { persist: false, notifyNative: false });
      expect(getLang()).toBe("en");
      expect(t("app.name")).toBe("Aarogya Mesh");
      expect(flagLabel("sunken_eyes")).toBe("Sunken eyes");

      setLang("hi", { persist: false, notifyNative: false });
      expect(getLang()).toBe("hi");
      expect(t("app.name")).toBe("आरोग्य जाल");
      expect(tx("flag.convulsions", "fallback")).toBe(hi["flag.convulsions"]);
      expect(flagLabel("sunken_eyes")).toBe(hi["dehy.sunken_eyes"]);

      setLang("kn", { persist: false, notifyNative: false });
      expect(getLang()).toBe("kn");
      expect(t("app.name")).toBe("ಆರೋಗ್ಯ ಸಂಜಾಲ");
      expect(tx("flag.convulsions", "fallback")).toBe(kn["flag.convulsions"]);
      expect(flagLabel("sunken_eyes")).toBe(kn["dehy.sunken_eyes"]);

      setLang("ta", { persist: false, notifyNative: false });
      expect(getLang()).toBe("ta");
      expect(t("app.name")).toBe("ஆரோக்கிய வலையமைப்பு");
      expect(tx("flag.convulsions", "fallback")).toBe(ta["flag.convulsions"]);
      expect(flagLabel("sunken_eyes")).toBe(ta["dehy.sunken_eyes"]);
    } finally {
      setLang(prev, { persist: false, notifyNative: false });
    }
  });

  it("parses valid languages from raw strings and query strings", () => {
    expect(parseLang("en")).toBe("en");
    expect(parseLang("HI")).toBe("hi");
    expect(parseLang(" kn ")).toBe("kn");
    expect(parseLang("TA")).toBe("ta");
    expect(parseLang("fr")).toBeNull();
    expect(parseLang(null)).toBeNull();
    expect(queryLang("?lang=kn")).toBe("kn");
    expect(queryLang("?lang=ta")).toBe("ta");
    expect(queryLang("?foo=1&lang=hi")).toBe("hi");
    expect(queryLang("?lang=invalid")).toBeNull();
    expect(queryLang("")).toBeNull();
  });

  it("notifies AarogyaNativeBridge.setLanguage safely when present", () => {
    const spy = vi.fn();
    notifyNativeLang("ta", { AarogyaNativeBridge: { setLanguage: spy } });
    expect(spy).toHaveBeenCalledWith("ta");
    expect(() => notifyNativeLang("hi", {})).not.toThrow();
    expect(() => notifyNativeLang("en", { AarogyaNativeBridge: { setLanguage: () => { throw new Error("boom"); } } })).not.toThrow();
  });
});
