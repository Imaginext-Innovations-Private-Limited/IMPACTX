# Engineering decisions: what the judges should learn about our mindset

## User problem → measurable behavior
A person sees a threatening WhatsApp message or a UPI collect request. We reduce the decision time by allowing quick paste/upload; reveal precise matched wording; show concrete steps; link to official reporting channels. The user can **disagree with the tool and verify independently**.

## Decision 1 — Narrow the first release deliberately
**Rejected:** intercept live phone calls, read private WhatsApp chats, link directly to UPI apps, train a massive deepfake detector in two days. They need sensitive permissions, partner APIs and extensive security review. **Selected:** working browser-based, real-time **analysis of user-supplied text**, screenshots and optional microphone dictation.

## Decision 2 — Explainability over flashy metrics
Instead of a misleading “98% fraud confidence,” show each rule match with the exact snippet of user-supplied text, a short rationale and actionable safety advice. The 0–10 display is a heuristic risk index, not statistical probability or measured accuracy.

## Decision 3 — Hybrid instead of LLM-only
An explicit engine handles high-risk, well-understood behaviors (asking for UPI PIN to receive money, collecting OTPs, remote access demands). A tiny local ML classifier trained on **synthetic** text can request a Review when language resembles examples but no strong rules match. The model's performance is not validated externally; no invented accuracy numbers.

## Decision 4 — Sensitivity to false alarms
Legitimate KYC messages and cybersecurity awareness content can contain suspicious keywords. Generic urgency is only a weak signal; scores must not claim verified fraud. UI always says “not enough context” when the text is too short and “no clear signal” rather than “safe” when nothing matches.

## Decision 5 — Privacy and consent
Never silently read someone's messages. Never save scans to a database or log their text. Uploaded images are OCR'd in memory. Mic capture is permissioned and browser dependent, and may use an external browser speech provider. For commercial production: privacy impact assessment, TLS, access control, server limits, consent, data retention policy, independent security testing and legal review.

## Decision 6 — Evaluate failure cases
Test on at least four fraud classes (digital arrest, KYC, courier, UPI), legitimate transactional messages, deliberate scam-awareness messages, short ambiguous text, Hindi text, manipulated messages and OCR errors. Measure false positives and false negatives on a disjoint labeled holdout; **don't** report scores from training sentences as a real-world benchmark.

## Future roadmap (clearly not implemented)
- Validated, consented real-world corpus and calibrated classifier with confidence and abstention.
- Multiple Indian languages, OCR quality enhancement and trusted contact verification.
- User-consented native Android integration where platform and legal constraints allow.
- Escalation to accredited human help and vetted reporting services.

## Questions judges might ask
**What is the actual AI?** Local TF-IDF character n-gram classifier with Linear SVM (selected for v2.1 after comparative synthetic evaluation and regression testing), working alongside a transparent hand-coded rule set. Limited synthetic training means currently experimental.

**Does it listen to WhatsApp or intercept calls?** No. Only user-supplied text/screenshot or browser microphone transcription. This boundary is intentional and documented.

**Does a score of 9 mean 90% chance of scam?** No. It's a relative risk index; it has not been calibrated against real-world prevalence.

**What if a model labels a legitimate bank reminder as fraud?** We treat generic KYC language as a weaker signal and clearly suggest independent verification, not blanket certainty. We track false positives in testing.

**What did the team prioritize?** Safety impact, visible end-to-end workflow, transparent architecture, testability, privacy and clean deployment over a long list of incomplete integrations.


## v1.2 — A voice-first multilingual accessibility layer (23 Nov 2026)

**User need:** Fluent speakers of Bengali, Hindi, Kannada, Telugu and Odia may not be comfortable reading/writing those scripts. A text-only translation selector would exclude people who need spoken warnings.

**Decision:** Keep the proven v1.1.3 two-panel web design. Select the output language independently from input; provide short, preauthored risk-level-specific advice; speak only that advice (never the supplied transcript, URLs, or OTP); prefer consented team-member voice recordings for pronunciation; fall back to a matching browser speechSynthesis voice. Disable voice playback when no compatible playback exists, rather than silently substituting an English voice. Offer a separate local voice-pack recorder.

**Scope limit:** Conservative native-script rule additions support selected arrest/payment/KYC/secret-request phrases, not broad semantic understanding of Indian regional languages. The script may be reviewed and recorded by fluent teammates, but formal translation validation and independent multilingual fraud accuracy testing remain uncompleted. UI navigation remains English; Hindi/Bengali/Kannada/Telugu/Odia safety summaries/actions are localized. OCR remains English/Hindi; browser voice recognition may need cloud processing and vary by region and device.

**Privacy:** Audio prompts are fixed localized strings selected by risk level. No user message, extracted secrets, matched evidence, or complaint draft is supplied to text-to-speech. Locally recorded voice packs require explicit contributor consent prior to publication.

**Testing:** New tests verify multilingual API shapes, output/input-language independence, four native-script synthetic scam examples, four safe OTP messages, and voice script secret isolation. No evidence of population-level detection accuracy is claimed.
