WELFARE SCHEME NAVIGATOR — MYSQL EDITION

WINDOWS: FIRST INSTALLATION
1. Extract this entire ZIP into a new folder. Keep the old project folder if you have existing customer records.
2. Install 64-bit Python 3.11 or 3.12. Enable “Add python.exe to PATH” during installation.
3. Install MySQL Community Server 8.4 from https://dev.mysql.com/downloads/mysql/ .
   In MySQL Configurator, set your root password, keep the local port (usually 3306),
   configure MySQL as a Windows service and start it. Workbench is optional.
4. Double-click SETUP_MYSQL.bat. Enter the port, root username and root password
   at the prompts. Password entry is hidden. The setup creates welfare_navigator,
   project tables and a dedicated local app user. The root password is not saved.
5. For image or scanned-PDF OCR, run SETUP_OCR_WINDOWS.bat once. Allow the
   Windows installation prompt. Internet is required for the four language packs.
6. Double-click START_WINDOWS.bat and open the printed localhost address.
   Run CHECK_WINDOWS.bat for the workflow tests and a live MySQL connection check.
7. If Ollama already lists qwen2.5:3b and bge-m3, keep your existing models.
   In Admin & research > Knowledge base, refresh embeddings for this new catalogue.
   See SETUP.md for AI, voice, admin access and other operating systems.

UPDATING THE PREVIOUS MYSQL EDITION
Stop the old server using Ctrl+C. Extract the updated ZIP. Copy the contents
of the new WelfareNavigator folder into the existing MySQL project folder and
replace the supplied project files. Keep your existing local_data and .venv.
Run START_WINDOWS.bat. Startup creates the new member_activity table in the
existing database. Existing family codes, members, drafts and reports still work.

ADMIN ACCESS AND VOICE
First installation creates local_data/ADMIN_FIRST_LOGIN.txt. If the MySQL
database already has an admin password and the file is missing, double-click
RESET_ADMIN_WINDOWS.bat and press Y for a new file. Open it and sign in under
Admin & research. This changes the app admin login only. When you choose a
personal password in Privacy & security, the first-login file is removed.

For microphone input run SETUP_LOCAL_VOICE.bat once and wait for success.
Open the local URL, choose the language and allow the microphone. In Family
profiles dictate a name, age or state, review it, and click Add member or
Save changes to selected member. In AI Navigator stop recording, review the
transcript and click Save spoken answer. Check the value after reopening
the same member. Draft fields use Save progress. Use a short answer such as
"Karnataka", "Yes" or "70". For a microphone error check the selected input
device in Windows Settings > System > Sound and the browser's mic permission.

DASHBOARD AND FAMILY PROFILES
Open the site's main address to browse the dashboard. The menu, scheme search
and language controls work before login. Open Family profiles and choose the
Register family card to get a private code, then use the Log in card with that
code. Save the code for the customer's next visit. Add individual members in
the family and choose Current family member before recording personal work.
For another customer use Log out of family to return to the public dashboard.
Select Member records to review that person's saved activities, previous scheme
checks, draft checklists, confirmed scans and PDF reports. Downloaded PDFs belong
to the customer; remove them from a shared laptop after transfer.

MY WELFARE REPORT
Select the person in Current family member, then open My welfare report. Possible
matches, pending checks and unmet rules are separate. A name alone is insufficient
for a decision. Download PDF creates a dated copy in MySQL for that person.
An application draft is a separate document for one scheme. The official service
makes the final decision.

WHAT-IF SIMULATOR
Example: select a member aged 70, choose the senior health scheme, then try 69.
The simulator shows which rule changes. The member's saved age and report stay at 70.

OCR
Choose Document scanner, the member, the FILE language and a clear image or PDF.
Review the extracted fields and the page-by-page text. Correct and confirm the
fields before copying them into a draft. Only the confirmed preparation fields are
saved. Low-contrast images, handwriting and complex tables can need correction.

KARNATAKA
Explore schemes > Government > Karnataka lists 61 local scheme routes. Five
state guarantees have guided questions. A further 56 myScheme entries contain
published criteria for applicant review, including exclusions when available.
The expandable Karnataka directory includes all 372 Karnataka records in the
November 3 register snapshot. Budget lines and audit entries can refer to the same
programme. They are labelled separately and do not imply personal eligibility.
Consult the linked official directory for changes since that snapshot.

EXISTING SQLITE CUSTOMERS (OPTIONAL)
Stop the old app and keep its entire folder. After MySQL setup, open PowerShell
in the NEW project folder and run, substituting your old database path:
.\.venv\Scripts\python.exe migrate_profiles.py "C:\old-project\local_data\navigator.sqlite3"
The migration reads the old database without altering it. It imports members,
answers, drafts, checklist status, decisions, reminders and feedback. Because an
old shared browser may contain unrelated customers, each imported member gets a
separate private code. The printed local file contains those codes. Give each
customer only their own code. A repeat skips previously imported member IDs.
Old custom scheme versions, admin logs and AI experiment history stay in the old
database. This edition starts with a new scheme catalogue.

MYSQL WORKBENCH
Connect to your local MySQL server, open Schemas > welfare_navigator > Tables.
households, visits, profiles: family ownership, visits and member answers.
decisions, drafts, checklist_items, confirmed_scans, reports: member-specific work.
reminders and feedback: notifications and ratings.
schemes, sources, karnataka_directory, vectors and blobs: catalogue and knowledge.
config, sessions, events, traces and experiments: administration and research.
