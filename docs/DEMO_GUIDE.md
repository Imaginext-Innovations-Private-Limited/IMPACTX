# Citizen and faculty walkthrough

Use fictional records. For the first demonstration, complete the installation and open the local app. Select a language in the header and open the menu. Open the dashboard, choose Family profiles, register a family, and log in with the issued code. Add a consented profile. Log out between customers.

## Seven-minute walkthrough

| Click | What to demonstrate |
|---|---|
| Home → Find schemes for me | A person can describe a need without knowing the programme name. Select a state and see one relevant question at a time. Try **Not sure**. |
| Menu → Family profiles | Select **Rao (demo)**, agree to save this fictional person, and add the member. Add **Anu (demo)** as another member. Select a member to see their own results. |
| Eligibility checker → Ayushman Bharat 70+ | Select Rao. With the fixture's recorded age 70 and citizenship answer, show the preliminary match. Open **Why this result?**, inspect the tested value and open the NHA FAQ. |
| What-if simulator → Ayushman | Change age from 70 to 69. Show the changed rule. Return to the member's eligibility checker to verify that the saved profile still says 70. |
| Explore schemes → Ayushman → View scheme | Ask “What Aadhaar document is needed for enrolment?” Inspect the answer mode, page or section and official link. With Ollama running and an index built, show semantic retrieval and generation. With Ollama unavailable, the app displays the source passages. |
| Document checklist → Application assistant | Mark a document ready. Enter a fictional name, preview and save. Download the draft PDF. My applications shows its local status and lets you resume, export or delete it. The official portal handles enrolment, signing and submission. |
| Family → Anu → Eligibility checker → education | The fictional school student has annual parental income of ₹120,000; the state examination selection is unknown. Show the pending check. The scheme detail identifies the particular 2026–27 notice and explains that the published date has passed. A university student would need a different verified scholarship route. |
| My welfare report → Download PDF | Show the summary, reasons, checklist, application steps, generation date and official links. Switch family members and compare the output. |

## Check the advanced pages

* **Comparison:** select two or three distinct schemes. Compare evidence, steps, dates and known restrictions on combining benefits.
* **Document scanner:** use a fictional image or text PDF with “Name: Demo User” and “Village: Demo Village”. Give consent, inspect original and extracted text, correct it, confirm fields, then use the application assistant's opt-in prefill. For images install Tesseract and language packs. PDFs are previewed temporarily inside the browser.
* **Centres:** try “Hyderabad” or “520001”. Check the directory date and link. A search outside the cache offers the current official CSC locator.
* **Reminders:** opt in to documents, dates or new matches. Save an incomplete draft. Refresh reminders after the next local maintenance cycle, then snooze or dismiss it.
* **Language and voice:** try the same scheme in Telugu and Hindi. Microphone input transcribes locally and lets you edit before submission. Read-aloud selects installed local voices. Text entry remains available.
* **Privacy:** export one fictional member, review the file, delete the member, and check that their own drafts disappear without affecting other members.

## Admin and research demonstration

1. Open the footer's Admin & research link. Use this laptop's first-login password. Open Manage schemes and review the version history.
2. Open Knowledge base. Pick an existing scheme ID and the URL/title of a real issuing authority PDF. Select the locally downloaded PDF or import its official HTML page. Enter the verification date and section; click import.
3. Refresh until the job is complete. Inspect extracted chunks, compare their contents with the original, and approve only faithful passages. Inactive chunks remain outside citizen retrieval. Deactivate superseded passages or flag a contradiction for review. Build the embedding index and inspect a search query.
4. In Manage schemes, save a draft, send it for review, check source IDs, and publish the reviewed version. Archiving removes the scheme from the citizen catalogue. New schemes can reuse or combine the typed question fields listed in seed/questions.json; state and category values are data.
5. Open Agent monitor after a citizen question. Show retrieved IDs, model availability, elapsed time and rule outcomes. In Audit logs, filter on a scheme ID and export events.
6. In AI experiments, run labelled eligibility tests. With a real model running, run the identical fictional questions with the baseline and RAG configurations. Choose a model tag, top-k and prompt version. Refresh job status. Inspect original evidence and mark each output's support and citation correctness. Research & analytics calculates observed counts and exports the results.
7. In System settings, download the content backup. Use a disposable copy of the app for a restore demonstration, then rebuild its semantic index. Use Privacy & security to set retention and rotate the password.

**Simple faculty introduction.** “Citizen konni questions ki answers istharu. Python official rules tho eligibility check chesthundi. Ollama official document nunchi relevant passage theesukuni simple language lo explain chesthundi. Citizen documents ready chesi draft prepare chesukuntaru. Final decision government department teesukuntundi.”
