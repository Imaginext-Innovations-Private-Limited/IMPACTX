# Who to ask, and what to ask for

Start small and local. Ten real bills with honest results beat any number of test bills.
Find contacts through official pages and your college network. Do not cold-call patients in
hospitals.

| Who | Why they can help | What to ask for |
|---|---|---|
| Your own family, friends and classmates | Fastest source of real bills, easy consent | Old bills from any hospital stay, with the consent form |
| College NSS unit or health club | Runs health camps and community visits | Introductions to families willing to share a bill; a slot to demo at a camp |
| Arogya Mitras at PM-JAY / Arogya Karnataka empanelled hospitals | They help scheme patients every day and know the common billing problems | 15 minutes to try the app on a sample bill and tell you what is wrong with it (field note, no patient data) |
| State Health Agency grievance cell (in Karnataka, Suvarna Arogya Suraksha Trust) | Decides scheme grievances | Whether a letter in the app's format is useful to them; anonymised examples of common grievance types |
| District consumer commission legal-aid clinic or a law college legal-aid cell | Sees overcharging complaints | Decided orders on hospital overcharging (public) to add as `decided_case` evaluations |
| Hospital billing or patient-help desk (any hospital willing) | Can say where the app misreads their bill format | A blank or specimen bill layout; feedback on the line-matching panel |
| A pharmacist | Knows MRP and strip-versus-tablet billing | Check the medicine rules and the "tablets or strips" question |

## Public sources you can use without anyone's permission

- Hospital stent and implant price lists (already used in `eval/crosswalk/`). Add more hospitals
  from more states to grow the brand table and the test set.
- Consumer commission orders on overcharging (e-Jagriti, court reporting services). Quote only
  the bill lines in the order, with the citation.
- NPPA notifications and its overcharging actions, for the knowledge base.

## A message you can send

> I'm an MSc Data Science student building Kharcha Kavach, a free app that checks hospital bills
> against NPPA price limits and PM-JAY rules and shows the proof for every rupee. Could I take
> 15 minutes of your time to show it on a sample bill and hear what it gets wrong? I'm not asking
> for any patient data.

Write down what they say in `field_notes.md` the same day, with the date and their role (not
their name unless they agree).
