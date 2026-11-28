# Evaluator walkthrough

[Repository home](../README.md) · [Shared pilot setup and permissions](SUPABASE_PILOT.md)

## Three-minute presentation

| Time | Show | Explain |
| --- | --- | --- |
| 0:00–0:40 | Open the live citizen site and select a lake in **Citizen lake map and guest reporting**. | Citizens can use the lake advisories even when they have no report to submit. A visible shoreline concern can prompt precautions, while the evidence remains subject to review. |
| 0:40–1:25 | Open the public rehearsal. Start it, save **Foam from a second view** at **North Inlet**, and download the draft from the resulting **Priority hotspot**. | Show the two supporting report IDs. The example demonstrates the prototype rule and keeps its data in the rehearsal session. |
| 1:25–2:10 | Open **Community Drives**. Show the public schedule and community sign-in. | Organizers propose drives, assigned lake operators approve them, and citizens register. Approved same-day drives appear on the homepage according to Bengaluru time. |
| 2:10–3:00 | Open the operator workspace if an assigned account is available. Show **Restoration tracker** and **Community impact** for a selected lake. | Explain who records corrective work, how citizens provide follow-up evidence, and what an operator must verify before the outcome appears in the dashboard. |

[Live citizen site](https://jalnetra-wine.vercel.app/) · [Public rehearsal](https://jalnetra-wine.vercel.app/?demo=1) · [Community Drives](https://jalnetra-wine.vercel.app/community.html) · [Operator sign in](https://jalnetra-wine.vercel.app/pilot.html?role=operator)

## Public rehearsal and offline fallback

1. Click **Start rehearsal**. North Inlet starts at **Watch**.
2. In **Offline demo images**, choose **Foam from a second view**, keep **North Inlet** selected, and click **Save observation**.
3. Open the **Priority hotspot**, then **Open complaint draft** and **Download draft**. Compare the report IDs in the export with the evidence displayed on screen.
4. Submit **Obscured view** to see **Needs review**. Use **Restart rehearsal** to reset the example.

For the offline version, run `node src/server.js --rehearsal` with Node.js 24 and open `http://127.0.0.1:3000`. The local rehearsal stores its example data in memory. The hosted rehearsal maintains an isolated browser session.

## Shared workflow with assigned accounts

Use a staging lake or a real scheduled event that the organizers authorize for evaluation.

1. Create an organizer account and confirm the email. Sign in on **Community Drives** and submit a drive with a lake, start date and time in IST, meeting point, and safety instructions.
2. Sign in as a different account assigned to operate that lake. Open **Community drives** and approve the proposal.
3. Open **Community Drives** as a citizen and register. For a drive scheduled on the current Bengaluru date, verify that the home page lists the correct lake, date, and start time.
4. Once the drive starts, record attendance from **Manage published cleanups** and mark the drive complete. Open the same lake's **Community impact** and check the completed-cleanup and attendance counts.
5. For restoration, start from an operator-verified pollution report. Assign a team, start the work, and record what was completed. As a citizen, upload a newer photo from the same sector and submit it for review in the tracker. As an operator, open and review that evidence and verify the result. Check the verified-restoration count.

Public rehearsal steps require no login. The shared workflow requires access to the organizer inbox and an assigned operator account. A public schedule or impact counter can be empty when no corresponding records exist.

## Automated checks

From the repository root, run `node --test`. The [Supabase tests](../supabase/tests/) cover lake role restrictions, drive approval and Bengaluru date boundaries, and community outcomes. Run them against a migrated test database using the [pilot setup guide](SUPABASE_PILOT.md). The SQL scripts roll back their fixtures.
