# RGCA — Regulator-Grounded Compliance Auditor

> An AI-lending fairness auditor that doesn't just compute bias metrics — it ties every finding to the **specific regulation** that governs it, checks whether that rule is actually **in force**, and **verifies** the generated report against the legal source text.

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [How It Works](#-how-it-works)
- [Architecture](#️-architecture)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [Tech Stack](#️-tech-stack)
- [Disclaimer](#️-disclaimer)
- [Contributors](#-contributors)
- [Acknowledgements](#-acknowledgements)

---

## 📌 Overview

Most fairness tools stop at "the approval ratio is 0.77." A compliance officer then asks: *"Is that illegal? In which country? Is the law even active yet?"*

**RGCA** closes that gap. It audits credit-decision models for bias across **three jurisdictions (US, EU, India)** and produces plain-English reports in which every legal claim is retrieved from a curated library of rule cards (one JSON per legal clause), labelled by pure code with no LLM (Applies, Not yet in force, Heuristic only, Wrong jurisdiction, Out of scope, or Needs human review), written by an LLM that must obey those labels and cite card IDs, and finally verified by a checker that confirms the cited cards exist, the labels were respected, and the obligation text is actually found in the saved source document.

> ⚖️ Design principle: **the LLM never decides the law.** Code decides applicability; the LLM only writes prose within those constraints.

---

## ✨ Key Features

| Feature                               | What it does                                                                                                                      |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Group fairness testing**      | Selection-rate ratios, Fisher exact p-values, TPR gaps, four-fifths screening, practical-significance band, Fairlearn cross-check |
| **Counterfactual "flip tests"** | Change *one* protected attribute on a rejected applicant; see if the decision flips                                             |
| **Proxy detection**             | Probe model tries to guess protected attributes from the columns an "unaware" model still sees                                    |
| **Proxy ablation**              | Removes leaking columns to test whether they actually *carry* the gap (and what it costs in AUC)                                |
| **Planted-bias scenarios**      | Clean vs. deliberately biased synthetic India-style data, so detection can be scored against known ground truth                   |
| **Rule cards (18)**             | Structured, schema-validated legal notes with clause, source, status, effective date, caveat, threshold                           |
| **Hybrid retrieval**            | Hard filter (jurisdiction + test type) → MiniLM + FAISS semantic rank + BM25 keyword rank → top-k                               |
| **Applicability checker**       | Deterministic 6-label classification — no LLM                                                                                    |
| **Verified reports**            | Groq-written report + 3 automated checks (citation, label-respect, evidence-in-source)                                            |
| **Web dashboard**               | 8-page Flask app with live audit, fairness, counterfactuals, legal lookup, scenarios, reports (JSON/PDF), settings                |

---

## 🔄 How It Works

1. Train two models (logistic and boosted) on credit data, with and without protected attributes.
2. Test for bias using group fairness, counterfactual flip tests and proxy checks.
3. Retrieve the matching legal rule cards for each finding.
4. Label each card with pure code (in force, heuristic, wrong jurisdiction, etc.).
5. Generate a plain-English report with the LLM, constrained by those labels.
6. Verify the report against the card library and the saved source documents.

---

## 🏗️ Architecture

```
            ┌────────────────────────────────────────────┐
            │  Datasets (German Credit, Taiwan Default)  │
            │      + synthetic India-style scenarios     │
            └──────────────────────┬─────────────────────┘
                                   ▼
        ┌───────────────────────────────────────────────┐
        │ Models: Logistic + HistGradientBoosting       │
        │ 5-fold cross-fitting (every row scored by a   │
        │ model that never saw it)                      │
        │ Variants: uses_protected  |  unaware          │
        └──────────────────────┬────────────────────────┘
                               ▼
   ┌──────────────┬───────────────────┬──────────────────┐
   │ Group        │ Counterfactual    │ Proxy check      │
   │ fairness     │ flip tests        │ + ablation       │
   └──────┬───────┴─────────┬─────────┴────────┬─────────┘
          └─────────────────┼──────────────────┘
                            ▼
                    FINDING (numbers)
                            ▼
   ┌───────────────────────────────────────────────────┐
   │ Retrieval  (filter → MiniLM/FAISS + BM25 → top 3) │
   └──────────────────────┬────────────────────────────┘
                          ▼
   ┌───────────────────────────────────────────────────┐
   │ Applicability checker  (pure code, 6 labels)      │
   └──────────────────────┬────────────────────────────┘
                          ▼
   ┌───────────────────────────────────────────────────┐
   │ Report writer  (Groq LLM, temperature 0,          │
   │ must cite card IDs & obey labels)                 │
   └──────────────────────┬────────────────────────────┘
                          ▼
   ┌───────────────────────────────────────────────────┐
   │ Verifier: citations exist? labels respected?      │
   │ obligation text found in source file?             │
   └───────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
RGCA/
├── app.py                  # Entry point — python app.py
├── web_app.py              # Flask app: pages + JSON API
├── requirements.txt
├── .env                    # GROQ_API_KEY (you create this)
│
├── src/                    # Pipeline (run in numeric order)
│   ├── 01_inspect_data.py        # Look at data before trusting it
│   ├── 03_fairness_tests.py      # Train models + group fairness
│   ├── 04a_counterfactual_tests.py
│   ├── 04b_proxy_check.py
│   ├── 04c_ablation.py
│   ├── 05_scenarios.py           # Clean vs planted bias
│   ├── 06_write_cards.py         # Generate + validate rule cards
│   ├── 07_test_checks.py         # Test retrieval + applicability
│   ├── data_loading.py           # Load + decode datasets
│   ├── models.py                 # Logistic / boosted, cross-fitting
│   ├── fairness.py               # Ratio, Fisher, Fairlearn checks
│   ├── counterfactuals.py        # Flip definitions + runner
│   ├── proxy_check.py            # Probe model + permutation importance
│   ├── scenarios.py              # Synthetic columns + bias planting
│   ├── card_schema.py            # Card schema + validation
│   ├── retrieval.py              # Hybrid FAISS + BM25 retrieval
│   ├── applicability.py          # 6-label checker (no LLM)
│   ├── report_writer.py          # Groq LLM report generation
│   └── verifier.py               # Post-hoc report verification
│
├── cards/                  # 18 rule cards + schema.json
├── sources/                # Saved regulatory texts (HTML/PDF) used for evidence checks
├── data/                   # German Credit + Taiwan credit-card datasets
├── reports/                # Generated CSV/JSON results
├── templates/              # Jinja2 pages (8 dashboard views)
└── static/                 # CSS + JS
```

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
echo "GROQ_API_KEY=your_key_here" > .env
python web_app.py
```

Open **http://127.0.0.1:5000**. Without a Groq key the dashboard still runs; only LLM report generation is disabled.

---

## ⚙️ Tech Stack

- **Backend:** Python, Flask, Jinja2
- **ML / Stats:** scikit-learn, pandas, NumPy, SciPy, Fairlearn
- **Retrieval:** sentence-transformers (`all-MiniLM-L6-v2`), FAISS, rank-bm25
- **LLM:** Groq API (`openai/gpt-oss-120b`, temperature 0)
- **Frontend:** HTML/CSS/JS templates

---

## ⚠️ Disclaimer

RGCA is an audit-support and research tool, not legal advice. Findings should be reviewed by qualified legal counsel.

---

## 👥 Contributors

| Members  | Name              |
| -------- | ----------------- |
| Member 1 | Meet Pujara       |
| Member 2 | Akshit Gajera     |
| Member 3 | Dharmik Ghevariya |
| Member 4 | Jashveer Gangani  |

---

## 🙏 Acknowledgements

- UCI Machine Learning Repository — South German Credit and Taiwan Default of Credit Card Clients datasets
- Regulatory sources: US eCFR/LII/CFPB, EUR-Lex (AI Act), RBI, NYC DCWP, India FREE-AI framework
