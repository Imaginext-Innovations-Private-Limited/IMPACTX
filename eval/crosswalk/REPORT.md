# Crosswalk evaluation on hospital-published text

Stent strings: 67 rows from 7 hospital price-list pages (27 carry the hospital's own DES/BMS label). Knee strings: 8 rows.

| Measure | With brand table | Without brand table |
|---|---|---|
| Recognised as a coronary stent | 67/67 (100%) | 60/67 (90%) |
| Right or higher ceiling, of labelled rows | 27/27 | 25/27 recognised rows |
| Lower ceiling than the true one (would inflate a claim) | 0 | 0 |

Knee component recognised correctly: 8/8.

Not recognised with the brand table: none.

Not recognised without it (what an unseen brand looks like): Pronova XR, Pronova CC/ SS, MITIGATOR, BIOMATRIX ALPHA, BIOFREEDOM, GRAFTMASTER, FLEXENIUM.

An unrecognised line is never claimed against: it is shown as 'no official price limit loaded'
and gets only arithmetic, duplicate and date checks. Recognition gaps cost coverage, not accuracy.
The brand table was compiled from these same lists, so the 'with' column shows that real spellings
("SYNERGY-XD, MEGATRON", "Xience Alpine / Xpedition", "INTEGRITY RESOLUTE (DES)") are handled; it is
not a measure of generalisation. Real consented bills are the next test (see pilot/).
