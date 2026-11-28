# Where each part of the test bills comes from

The three test bills are not real patient bills. They are built so that every rule fires, and
each part is marked as one of:

- **Official**: a price or rule taken from a dated government source (also in `data/sources.yaml`).
- **Published**: wording or a pattern taken from a public document (hospital price list, regulator
  study, audit report, decided case). The link is given.
- **Constructed**: chosen by us to exercise a rule. Nothing claims it happened on a real bill.

Hospitals, patients, bill numbers and GSTINs are fictional, and every page says TEST BILL.

## Prices and limits (all official)

| Value | Used in | Source |
|---|---|---|
| DES ceiling ₹39,186.03, BMS ₹10,762.15, excluding GST, from 1 Apr 2026 | Bills 1, 3 | NPPA order on coronary stents, 2026 revision (`nppa_stent_2026`) |
| Knee component ceilings (femoral ₹51,562.94, tibial tray with insert ₹35,332.73, patella ₹5,443.79) | Bill 2 | NPPA S.O. 3869(E), extended to 15 Jan 2027 (`nppa_knee_2024`, `nppa_knee_ext_2026`); the same figures appear on CARE Hospitals' published implant price list |
| GST 5% on medical devices and most medicines from 22 Sep 2025 | All | 56th GST Council decisions (`gst_2025_devices_medicines`) |
| Ceilings exclude GST; GST added only if paid or payable | All | NPPA S.O. 1551(E), 26 Mar 2024, and the knee ceiling definition ("excluding taxes, if any") |

### Medicine test bill (`tests/fixtures/medicine_bill/medicines_cash.json`)

| Value | Kind | Source |
|---|---|---|
| Ceilings: sodium chloride 0.9% 500 ml non-glass 35.71 and glass 41.95, Ringer lactate 500 ml 57.85, paracetamol 150 mg/ml 1 ml 5.34 | Official | NPPA S.O. 1581(E), 25.03.2026, Sl. Nos. 122, 121, 111, 91; exclusive of GST |
| Diclofenac listed only as a 50 mg capsule (Sl. No. 36) | Official | Same order; used to show a tablet is not matched to it |
| Hospital, quantities, rates, dates; pantoprazole line | Constructed | Ours, to test matching and arithmetic |

## Item names

| Line | Kind | Source |
|---|---|---|
| "Coronary Stent Xience Alpine 3.5x18" | Published | The brand as hospitals list it (Breach Candy: "XIENCE ALPINE / DES / ABBOTT"; Apollo; CARE; Fortis). Size suffix constructed |
| "Drug Eluting Stent (Everolimus) 3.0x28" | Official + constructed | NPPA's category name "Drug Eluting Stents (DES)"; everolimus is the drug in Xience-type stents; size constructed |
| "Femoral Component", "Tibial Tray with Insert", "Patella" | Published | Component labels on CARE Hospitals' implant price list and in the NPPA knee order |
| "PTCA Guide Wire", "Balloon Catheter", "PTCA Procedure Charges" | Constructed | Common angioplasty line names; not copied from a specific bill |
| "Inj Enoxaparin 40mg", "Tab Clopidogrel 75mg", "Tab Atorvastatin 40mg" | Constructed | Real medicines used around angioplasty; the MRPs on the test bill are invented |
| "Lipid Profile", "ECG", "Room Rent Twin Sharing", "Deluxe Room Upgrade", "Attendant Diet Charges" | Constructed | Generic line names |

Real Indian bill lines from the Hugging Face dataset `shaluyadav/newdatafiles` (for example
"K Wire 1.8mm", "Philos 3.5 3 Hole Ti", "ACUTE CARE ISOLATION") are used separately, in
`scripts/eval_public_lines.py`, to check that real implant lines are not mistaken for capped items.

## Error patterns

| Pattern on the test bill | Rule | Kind | Public evidence that it happens |
|---|---|---|---|
| Stent billed above the NPPA ceiling | PRC-STENT | Published pattern | NPPA demand notices after the 2017 cap: a hospital billed ₹60,000 and ₹1.25 lakh for stents (Medical Dialogues, Business Standard); NPPA asked 20 hospitals to refund ₹52 lakh to 80 patients (Medical Dialogues) |
| Stent type not printed | PRC-STENT condition | Official requirement | NPPA (12 Feb 2018) told hospitals to show the stent's cost, category and brand separately on the bill (Lok Sabha answer AU2781) |
| Scheme card holder made to pay | ENT-COVERED, ENT-CASH-DENIAL | Published pattern | CAG Report No. 11 of 2023 on PM-JAY found instances where patients had to pay as part of their treatment despite the cashless entitlement |
| Charges far above what the hospital paid (consumables, non-scheduled drugs) | Context for MRP and price rules | Published pattern | NPPA's 2018 analysis of four Delhi-NCR hospitals: margins up to 1,737% on consumables (three-way stopcock bought at ₹5.70, billed ₹106); Lok Sabha answer AU4730 |
| Inflated quantities of consumables | Context for quantity checks | Published pattern | The Gurugram dengue case that triggered NPPA's study: the family was billed for 616 syringes and 1,500 non-sterile gloves (as reported) |
| Charging extra over an advertised angioplasty price | Context | Decided case | NCDRC upheld orders against a Haryana hospital that charged a patient ₹1.05 lakh over its advertised angioplasty price (Medical Dialogues) |
| Item above printed MRP | PRC-MRP | Constructed | Selling above MRP is illegal under the Legal Metrology rules; the amounts are ours |
| Quantity × rate not equal to the amount; total above the sum of lines; duplicate test; more room days than nights; item dated outside the stay | ARI-*, CONV-* | Constructed | Common billing-error categories. Not tied to a specific published case |

## Links

- NPPA 2018 study coverage: https://www.indiaspend.com/hospitals-inflated-drug-prices-by-up-to-1737-govt-regulator-8-days-later-hes-transferred-92425
- Lok Sabha unstarred question 4730 (23 Mar 2018): https://eparlib.nic.in/bitstream/123456789/769490/1/AU4730.pdf
- Lok Sabha unstarred question 2781 on stent billing: https://eparlib.nic.in/bitstream/123456789/771833/1/AU2781.pdf
- CAG Report No. 11 of 2023, PM-JAY performance audit: https://cag.gov.in/uploads/download_audit_report/2023/04_Executive-Summary-064d22bab3b3f45.25634714.pdf
- Reporting on patients paying under PM-JAY (CAG): https://www.lokmattimes.com/politics/cag-report-reveals-beneficiaries-paid-money-for-treatment-under-ab-pmjay/amp
- NPPA stent refunds: https://medicaldialogues.in/stent-overpricing-20-hospitals-told-to-refund-rs-52-lakhs-to-80-patients
- Hospital fined for stent overcharging: https://medicaldialogues.in/new-delhi-metro-hospital-fined-rs-1-26-lakh-for-stent-overcharging
- NCDRC angioplasty overcharging: https://medicaldialogues.in/misleading-advertisements-overcharging-on-angioplasty-ncdrc-fines-gurugram-hospital
- Gurugram dengue bill coverage: https://www.heraldgoa.in/review/hospitals-inflated-drug-prices-by-up-to-1737-govt-regulator-8-days-later-hes-transferred/307266
- Hospital stent and implant price lists: see `eval/crosswalk/hospital_stent_strings.csv` and `data/sources.yaml` (`hospital_stent_lists`)

## bill5_outlier_extremes (outlier test)

Fictional, stamped TEST BILL, made by `make_bills.py` (BILL5). Every value is chosen to be
extreme or impossible: a stent at about 24 times its NPPA cap, an injection at over 100 times
its MRP, a misplaced zero (9,800 billed as 98,000), 45 ICU days for a 2-night stay, a test dated
2024, a 1 crore total against 28 lakh of lines, a zero line, a 3 paise line and a negative
return line. It checks that the app flags what its rules cover, reads edge values exactly as
printed, never crashes, and never invents a threshold for what no rule covers (12 stents and
10,000 tablets are listed as known gaps in the JSON).

## bill6_gst_on_treatment (GST test)

Fictional, stamped TEST BILL, made by `make_bills.py` (BILL6). A medical admission (dengue work-up)
where the hospital adds CGST 9% and SGST 9% on its services. The pattern (GST billed on treatment
that GST law exempts) is the one the rule checks; the amounts are invented. The rules it is checked
against are real and cited in `data/sources.yaml`: CBIC Circular 32/06/2018-GST Sl. No. 5
(treatment exempt), Notification 04/2022-CT(Rate) (ICU exempt; rooms taxable only above Rs 5000 a
day, from 18.07.2022) and Notification 03/2022-CT(Rate) (5% on those rooms).
